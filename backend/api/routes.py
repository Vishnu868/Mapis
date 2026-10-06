"""REST + WebSocket API. Every inspection runs the synchronous shield in a worker thread."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.agents.graph import run_pipeline
from backend.agents.testbed import make_environment
from backend.core.shield import Tier
from backend.db import EventLog, get_db, save_verdict, tier_counts

router = APIRouter()


class InspectRequest(BaseModel):
    session_id: str
    role: str = Field("assistant", description="user | assistant | tool | tool_response | memory_read | memory_write | system")
    source: str
    target: str
    content: str | None = None
    tool_name: str | None = None
    tool_call: dict | None = None


class PipelineRequest(BaseModel):
    task: str = "Summarise the vendor contracts in our shared drive and email me the key terms."
    scenario: str = "clean"          # clean | attack | decomposed
    web: dict[str, str] = {}
    files: dict[str, str] = {}
    session_id: str | None = None
    framework: str = "langgraph"     # langgraph | autogen


class Hub:
    """Fan-out of live verdicts to dashboard WebSockets."""

    def __init__(self) -> None:
        self.clients: list[WebSocket] = []

    async def send(self, payload: dict) -> None:
        for ws in list(self.clients):
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001 - drop dead sockets
                self.clients.remove(ws)


hub = Hub()


async def _record(db: AsyncSession, verdict: dict) -> dict:
    await save_verdict(db, verdict)
    await hub.send({"type": "verdict", "data": verdict})
    return verdict


@router.get("/health")
async def health(request: Request):
    shield = request.app.state.shield
    return {"status": "ok", "detector": shield.detector.name, "store": shield.store.kind, "time": datetime.utcnow().isoformat()}


@router.post("/inspect")
async def inspect(req: InspectRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Tap endpoint: call before delivering any agent message, tool output or memory read/write."""
    shield = request.app.state.shield
    try:
        verdict = (await run_in_threadpool(shield.inspect, req.model_dump())).to_dict()
    except Exception as exc:  # noqa: BLE001
        logger.exception("inspection failed")
        if shield.cfg.fail_mode == "open":
            return {"tier": "PASS", "delivered": True, "error": str(exc), "fail_mode": "open"}
        raise HTTPException(503, f"inspection failed; fail-closed: {exc}") from exc
    return await _record(db, verdict)


@router.post("/pipeline/run")
async def pipeline(req: PipelineRequest, request: Request, db: AsyncSession = Depends(get_db)):
    shield = request.app.state.shield
    env = make_environment(req.scenario, req.web, req.files)
    if req.framework == "autogen":
        from backend.agents.autogen_testbed import run_autogen_pipeline as runner
    else:
        runner = run_pipeline
    result = await run_in_threadpool(runner, shield, env, req.task, "me@corp.com", req.session_id)
    for verdict in result["events"]:
        await _record(db, verdict)
    return result


# ── benchmark replay (Session inspector tab) and measured results (Results tab) ───────────────────────────
from pathlib import Path  # noqa: E402
import json as _json  # noqa: E402
import uuid as _uuid  # noqa: E402

_ROOT = Path(__file__).resolve().parents[2]
_SETS = {"multihop": "mapis_bench_multihop_v1.jsonl", "realharm": "mapis_bench_realharm_v1.jsonl", "v1": "mapis_bench_v1.jsonl",
         "decomposed": "mapis_bench_decomposed_v1.jsonl", "bipia": "mapis_bench_bipia_v1.jsonl", "independent": "mapis_bench_independent_v1.jsonl"}
_NOT_RUNTIME = {"attacker_instruction", "tool_response_template"}
_cache: dict[str, list[dict]] = {}


def _test_sessions(name: str) -> list[dict]:
    if name not in _cache:
        path = _ROOT / "data" / "mapis_bench" / _SETS[name]
        rows = [_json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()] if path.exists() else []
        _cache[name] = [r for r in rows if r["split"] in ("test", "external")]
    return _cache[name]


@router.get("/samples")
async def samples(dataset: str = "multihop", limit: int = 60):
    """Held-out test sessions a reviewer can replay: attacks and their benign twins."""
    if dataset not in _SETS:
        raise HTTPException(400, f"dataset must be one of {sorted(_SETS)}")
    rows = _test_sessions(dataset)
    attacks = [r for r in rows if r["is_attack"]][: limit // 2]
    benign = [r for r in rows if not r["is_attack"]][: limit // 2]
    return [{"sample_id": r["sample_id"], "attack": r["is_attack"], "attack_class": r.get("mapis_attack_class"),
             "vector": (r.get("provenance") or {}).get("attack_vector"), "benign_kind": r.get("benign_kind"),
             "hops": len(r["messages"]), "task": next((m.get("content") or "" for m in r["messages"] if m["role"] == "user"), "")[:160]}
            for r in attacks + benign]


class ReplayRequest(BaseModel):
    dataset: str = "multihop"
    sample_id: str


@router.post("/replay")
async def replay(req: ReplayRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Replay one benchmark session through the live shield, hop by hop, exactly as the benchmark does."""
    if req.dataset not in _SETS:
        raise HTTPException(400, "unknown dataset")
    sample = next((r for r in _test_sessions(req.dataset) if r["sample_id"] == req.sample_id), None)
    if not sample:
        raise HTTPException(404, "no such test session")
    shield, sid, out = request.app.state.shield, f"replay-{_uuid.uuid4().hex[:8]}", []
    for m in sample["messages"]:
        if m["role"] in _NOT_RUNTIME:
            continue
        event = {k: m.get(k) for k in ("role", "source", "target", "content", "tool_name", "tool_call", "tool_calls", "tool_response")}
        verdict = (await run_in_threadpool(shield.inspect, {"session_id": sid, **event})).to_dict()
        verdict["tool_call"] = m.get("tool_call")
        out.append(verdict)
        await _record(db, verdict)
    held = next((v for v in out if v["tier"] in ("QUARANTINE", "BLOCK")), None)
    return {"session_id": sid, "dataset": req.dataset, "sample_id": sample["sample_id"], "attack": sample["is_attack"],
            "attack_class": sample.get("mapis_attack_class"), "vector": (sample.get("provenance") or {}).get("attack_vector"),
            "benign_kind": sample.get("benign_kind"), "notes": sample.get("conversion_notes", ""),
            "held_at_hop": held["hop"] if held else None,
            "outcome": ("attack stopped" if held else "attack MISSED") if sample["is_attack"] else ("false alarm" if held else "benign session passed"),
            "events": out}


@router.get("/results")
async def results():
    """Measured benchmark numbers (results/*.json written by scripts/benchmark.py on the GPU machine)."""
    out = {}
    for key, rel in {"benchmark": "results/benchmark.json", "llamaguard": "results/benchmark_llamaguard.json",
                     "nemo": "results/benchmark_nemo.json", "seeds": "results/seeds/summary.json", "independent": "results/benchmark_independent.json"}.items():
        path = _ROOT / rel
        if path.exists():
            out[key] = _json.loads(path.read_text(encoding="utf-8"))
    return out


@router.get("/events")
async def events(limit: int = 100, session_id: str | None = None, min_tier: Tier = Tier.PASS, db: AsyncSession = Depends(get_db)):
    query = select(EventLog).order_by(EventLog.id.desc()).limit(limit)
    if session_id:
        query = query.where(EventLog.session_id == session_id)
    tiers = [t.value for t in Tier if t.severity >= min_tier.severity]
    rows = (await db.execute(query.where(EventLog.tier.in_(tiers)))).scalars().all()
    return [r.to_dict() for r in rows]


@router.post("/quarantine/{event_id}/{action}")
async def review(event_id: str, action: str, db: AsyncSession = Depends(get_db)):
    if action not in ("release", "reject"):
        raise HTTPException(400, "action must be release or reject")
    row = (await db.execute(select(EventLog).where(EventLog.event_id == event_id))).scalar_one_or_none()
    if not row or row.tier != Tier.QUARANTINE.value:
        raise HTTPException(404, "no such quarantined event")
    row.status = "released" if action == "release" else "rejected"
    await db.commit()
    await hub.send({"type": "review", "data": row.to_dict()})
    return row.to_dict()


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    counts = await tier_counts(db)
    total = sum(counts.values())
    return {"total": total, "tiers": {t.value: counts.get(t.value, 0) for t in Tier},
            "intercept_rate": round(100 * (total - counts.get("PASS", 0)) / total, 2) if total else 0.0}


@router.get("/sessions/{sid}/trace")
async def trace(sid: str, db: AsyncSession = Depends(get_db)):
    """Forensic report: every non-PASS event of the session with its propagation path."""
    rows = (await db.execute(select(EventLog).where(EventLog.session_id == sid, EventLog.tier != "PASS").order_by(EventLog.id))).scalars().all()
    if not rows:
        raise HTTPException(404, "no flagged events for this session")
    return {"session_id": sid, "events": [r.to_dict() for r in rows]}


@router.delete("/sessions/{sid}")
async def reset_session(sid: str, request: Request):
    request.app.state.shield.reset(sid)
    return {"reset": sid}


@router.post("/sessions/{sid}/channels/release")
async def release(sid: str, source: str, target: str, request: Request):
    request.app.state.shield.release_channel(sid, f"{source}->{target}")
    return {"released": f"{source}->{target}"}


@router.websocket("/ws")
async def ws(websocket: WebSocket):
    await websocket.accept()
    hub.clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in hub.clients:
            hub.clients.remove(websocket)
