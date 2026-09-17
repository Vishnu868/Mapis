"""
MAPIS API Routes
================
All REST API endpoints for the MAPIS backend.
"""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from backend.models.schemas import (
    ScanRequest, ScanResponse, PipelineRunRequest, PipelineRunResponse,
    AlertResponse, SessionSummaryResponse, StatsResponse, TrustDecision
)
from backend.models.database import AlertLog, MessageLog, get_db
from backend.core.trust_scorer import trust_scorer
from backend.agents.pipeline import run_pipeline

router = APIRouter()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active_connections.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active_connections.remove(ws)

    async def broadcast(self, data: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                pass

manager = ConnectionManager()


# ── Health Check ───────────────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "MAPIS",
        "timestamp": datetime.utcnow().isoformat()
    }


# ── Core: Scan a Single Message ────────────────────────────────────────────

@router.post("/scan", response_model=ScanResponse)
async def scan_message(
    request: ScanRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Scan a single inter-agent message through MAPIS trust scorer.
    This is the core API endpoint — call this before passing any
    message from one agent to another.
    """
    try:
        trust_score = trust_scorer.score_message(
            session_id=request.session_id,
            source_agent=request.source_agent,
            target_agent=request.target_agent,
            message=request.message,
            metadata=request.metadata
        )

        # Persist to DB if flagged
        if trust_score.decision in [TrustDecision.BLOCK, TrustDecision.WARN]:
            alert = AlertLog(
                session_id=request.session_id,
                source_agent=request.source_agent,
                target_agent=request.target_agent,
                decision=trust_score.decision,
                final_score=trust_score.final_score,
                pattern_hits=trust_score.pattern_hits,
                explanation=trust_score.explanation,
                timestamp=datetime.utcnow()
            )
            db.add(alert)

        # Always log to message log
        msg_log = MessageLog(
            session_id=request.session_id,
            source_agent=request.source_agent,
            target_agent=request.target_agent,
            message_hash=trust_score.message_hash,
            raw_score=trust_score.raw_score,
            final_score=trust_score.final_score,
            session_penalty=trust_score.session_penalty,
            decision=trust_score.decision,
            explanation=trust_score.explanation,
            timestamp=datetime.utcnow()
        )
        db.add(msg_log)
        await db.commit()

        # Broadcast to WebSocket clients (live dashboard)
        await manager.broadcast({
            "type": "scan_result",
            "data": trust_score.dict()
        })

        return ScanResponse(
            success=True,
            trust_score=trust_score,
            blocked=trust_score.decision == TrustDecision.BLOCK,
            warned=trust_score.decision == TrustDecision.WARN,
            message=trust_score.explanation
        )

    except Exception as e:
        logger.error(f"Scan error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ── Run Full Pipeline ──────────────────────────────────────────────────────

@router.post("/pipeline/run", response_model=PipelineRunResponse)
async def run_agent_pipeline(
    request: PipelineRunRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Run the full multi-agent pipeline with MAPIS monitoring.
    Inject a task (or an attack payload) and see MAPIS in action.
    """
    session_id = request.session_id or str(uuid.uuid4())

    result = run_pipeline(
        task=request.task,
        session_id=session_id
    )

    # Persist all events to DB
    for event in result.get("events", []):
        if event.get("decision") in ["BLOCK", "WARN"]:
            alert = AlertLog(
                session_id=session_id,
                source_agent=event.get("source_agent", "unknown"),
                target_agent=event.get("target_agent", "unknown"),
                decision=event.get("decision"),
                final_score=event.get("final_score", 0),
                pattern_hits=event.get("pattern_hits", []),
                explanation=event.get("explanation", ""),
                timestamp=datetime.utcnow()
            )
            db.add(alert)

    await db.commit()

    # Broadcast to dashboard
    await manager.broadcast({
        "type": "pipeline_result",
        "data": result
    })

    return PipelineRunResponse(**result)


# ── Alerts ─────────────────────────────────────────────────────────────────

@router.get("/alerts", response_model=list[AlertResponse])
async def get_alerts(
    limit: int = 50,
    session_id: str = None,
    db: AsyncSession = Depends(get_db)
):
    """Get recent alerts (BLOCK and WARN events)."""
    query = select(AlertLog).order_by(AlertLog.timestamp.desc()).limit(limit)
    if session_id:
        query = query.where(AlertLog.session_id == session_id)

    result = await db.execute(query)
    alerts = result.scalars().all()

    return [
        AlertResponse(
            id=a.id,
            session_id=a.session_id,
            source_agent=a.source_agent,
            target_agent=a.target_agent,
            decision=a.decision,
            final_score=a.final_score,
            pattern_hits=a.pattern_hits or [],
            explanation=a.explanation,
            timestamp=a.timestamp.isoformat() if a.timestamp else ""
        )
        for a in alerts
    ]


@router.delete("/alerts/{alert_id}")
async def delete_alert(alert_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a specific alert."""
    result = await db.execute(select(AlertLog).where(AlertLog.id == alert_id))
    alert = result.scalar_one_or_none()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    await db.delete(alert)
    await db.commit()
    return {"message": "Alert deleted"}


# ── Sessions ───────────────────────────────────────────────────────────────

@router.get("/sessions/{session_id}", response_model=SessionSummaryResponse)
async def get_session(session_id: str):
    """Get session history and statistics."""
    summary = trust_scorer.get_session_summary(session_id)
    if "error" in summary:
        raise HTTPException(status_code=404, detail=summary["error"])
    return summary


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str):
    """Clear a session's in-memory state."""
    trust_scorer.clear_session(session_id)
    return {"message": f"Session {session_id} cleared"}


# ── Stats / Dashboard ──────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get overall system statistics for the dashboard."""
    total_messages = await db.scalar(select(func.count(MessageLog.id)))
    total_blocked  = await db.scalar(select(func.count(AlertLog.id)).where(AlertLog.decision == "BLOCK"))
    total_warned   = await db.scalar(select(func.count(AlertLog.id)).where(AlertLog.decision == "WARN"))
    total_sessions = await db.scalar(select(func.count(func.distinct(MessageLog.session_id))))

    total_messages = total_messages or 0
    total_blocked  = total_blocked  or 0
    total_warned   = total_warned   or 0
    total_sessions = total_sessions or 0
    total_allowed  = total_messages - total_blocked - total_warned
    block_rate     = (total_blocked / total_messages * 100) if total_messages > 0 else 0.0

    return StatsResponse(
        total_sessions=total_sessions,
        total_messages=total_messages,
        total_blocked=total_blocked,
        total_warned=total_warned,
        total_allowed=max(0, total_allowed),
        block_rate=round(block_rate, 2),
        top_attack_types=[]  # populated in future version
    )


# ── WebSocket (Live Dashboard) ─────────────────────────────────────────────

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live dashboard updates."""
    await manager.connect(websocket)
    logger.info("WebSocket client connected")
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back any ping
            await websocket.send_json({"type": "pong", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info("WebSocket client disconnected")
