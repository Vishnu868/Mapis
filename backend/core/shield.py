"""MapisShield: the stateful inspection of one event.

inspect() is synchronous and framework-agnostic: LangGraph nodes, the FastAPI
tap and the benchmark replay all call the same function.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum

from . import features as F
from . import session as S
from .context import chunk_spans, event_text, normalize_hop
from .detector import load_detector
from .store import make_store

TRUSTED_ROLES = {"user", "system"}


class Tier(str, Enum):
    PASS = "PASS"
    FLAG = "FLAG"
    QUARANTINE = "QUARANTINE"
    BLOCK = "BLOCK"

    @property
    def severity(self) -> int:
        return list(Tier).index(self)


@dataclass
class Verdict:
    event_id: str
    session_id: str
    hop: int
    source: str
    target: str
    role: str
    tier: Tier
    trust: float
    model_trust: float | None
    features: dict
    reasons: list[str]
    trace: list[dict]
    detector: str
    latency_ms: float
    preview: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def delivered(self) -> bool:
        return self.tier in (Tier.PASS, Tier.FLAG)

    def to_dict(self) -> dict:
        return {**asdict(self), "tier": self.tier.value, "delivered": self.delivered}


class MapisShield:
    def __init__(self, settings=None, store=None, detector=None, features_enabled=("instruction", "drift", "provenance", "behaviour")):
        from backend.config import get_settings

        self.cfg = settings or get_settings()
        self.store = store or make_store(self.cfg.redis_url, self.cfg.session_ttl)
        self.detector = detector or load_detector(self.cfg.model_path)
        self.enabled = set(features_enabled)

    # ── tiers ────────────────────────────────────────────────────────────
    def tier_for(self, trust: float) -> Tier:
        c = self.cfg
        return Tier.PASS if trust >= c.pass_at else Tier.FLAG if trust >= c.flag_at else \
            Tier.QUARANTINE if trust >= c.quarantine_at else Tier.BLOCK

    # ── main entry ───────────────────────────────────────────────────────
    def inspect(self, event: dict) -> Verdict:
        """event: session_id, role, source, target, content and optional tool_name / tool_call(s)."""
        t0 = time.perf_counter()
        sid = event["session_id"]
        state = self.store.state(sid)
        state["hop"] += 1
        hop = normalize_hop({**event, "hop": state["hop"]})
        window = self.store.hops(sid)
        channel = f"{hop['source']}->{hop['target']}"

        model_trust, feats, reasons, trace, name, extra = None, {}, [], [], "n/a", {}
        if hop["role"] in TRUSTED_ROLES:  # user input is the trust anchor; direct jailbreaks are out of scope
            trust = 1.0
        elif channel in state["suspended"]:
            trust, reasons = 0.0, [f"channel {channel} is suspended after an earlier BLOCK"]
        else:
            texts, signals = S.prepare(state, window, hop, self.detector.use_context, self.cfg.window_hops)
            model_trust, worst = self.detector.score_chunks(texts, hop)
            spans = chunk_spans(len(event_text(hop)))
            a, b = spans[min(worst, len(spans) - 1)]
            extra = {"worst_chunk": {"index": worst + 1, "of": len(spans), "chars": [a, b], "snippet": event_text(hop)[a:b][:300]},
                     "signals": signals}
            name = self.detector.name
            trust, feats, reasons, trace = self._fuse(model_trust, hop, state, window)

        tier = self.tier_for(trust)
        if tier is Tier.BLOCK and channel not in state["suspended"]:
            state["suspended"].append(channel)
        if tier is not Tier.PASS:
            state["sensitivity"] = min(self.cfg.sensitivity_cap, state["sensitivity"] + self.cfg.sensitivity_step)
        if tier is not Tier.PASS and not trace:
            trace = [self._trace_row(hop, "origin")]

        S.commit(state, window, hop, 1.0 - trust)
        self.store.push(sid, hop)
        self.store.save(sid, state)

        return Verdict(
            event_id=uuid.uuid4().hex[:16], session_id=sid, hop=hop["hop"], source=hop["source"], target=hop["target"],
            role=hop["role"], tier=tier, trust=round(trust, 4),
            model_trust=None if model_trust is None else round(model_trust, 4),
            features=feats, reasons=reasons, trace=trace if tier is not Tier.PASS else [], detector=name,
            latency_ms=round((time.perf_counter() - t0) * 1000, 2),
            preview=(hop["content"] or F.action_text(hop))[:160], extra=extra,
        )

    # ── fusion ───────────────────────────────────────────────────────────
    def _fuse(self, model_trust: float, hop: dict, state: dict, window: list[dict]):
        c, on = self.cfg, self.enabled
        instr, instr_hits = F.instruction_risk(hop) if "instruction" in on else (0.0, [])
        drift = F.drift_risk(state["goal"], hop) if "drift" in on else 0.0
        prov, matches = F.provenance_risk(hop, state) if "provenance" in on else (0.0, [])
        behav, behav_why = F.behaviour_risk(hop, state) if "behaviour" in on else (0.0, "")

        survive = model_trust
        for weight, risk in ((c.w_instruction, instr), (c.w_drift, drift), (c.w_provenance, prov), (c.w_behaviour, behav)):
            survive *= 1.0 - weight * risk  # noisy-OR over independent signals
        risk = min(1.0, (1.0 - survive) * (1.0 + state["sensitivity"]))
        trust = 1.0 - risk

        feats = {"instruction": round(instr, 3), "drift": round(drift, 3), "provenance": round(prov, 3), "behaviour": round(behav, 3)}
        reasons = []
        if model_trust < c.pass_at:
            reasons.append(f"classifier trust {model_trust:.2f}")
        if instr_hits:
            reasons.append(f"instruction-like text in a data channel ({len(instr_hits)} cue(s))")
        trace = []
        for ind in matches:
            origin = state["taint"][ind]
            reasons.append(f"'{ind}' first appeared in untrusted hop {origin['hop']} ({origin['source']}) and now reaches an action")
            trace = self._propagation(ind, origin["hop"], window, hop)
        if behav_why:
            reasons.append(behav_why)
        if state["sensitivity"]:
            reasons.append(f"session sensitivity +{state['sensitivity']:.2f} after earlier flags")
        return trust, feats, reasons, trace

    # ── forensic trace ───────────────────────────────────────────────────
    @staticmethod
    def _trace_row(hop: dict, kind: str, indicator: str | None = None) -> dict:
        return {"hop": hop["hop"], "source": hop["source"], "target": hop["target"], "role": hop["role"], "kind": kind,
                "indicator": indicator, "snippet": (hop["content"] or F.action_text(hop))[:200]}

    def _propagation(self, indicator: str, origin_hop: int, window: list[dict], current: dict) -> list[dict]:
        """Every hop that carried the indicator, from its untrusted origin to the action using it."""
        rows = []
        for h in window:
            if h["hop"] >= origin_hop and indicator in F.hop_indicators(h):
                rows.append(self._trace_row(h, "origin" if h["hop"] == origin_hop else "relay", indicator))
        rows.append(self._trace_row(current, "action", indicator))
        return rows

    # ── session helpers ──────────────────────────────────────────────────
    def reset(self, sid: str) -> None:
        self.store.drop(sid)

    def release_channel(self, sid: str, channel: str) -> None:
        state = self.store.state(sid)
        state["suspended"] = [c for c in state["suspended"] if c != channel]
        self.store.save(sid, state)
