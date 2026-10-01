"""Forensic log: one row per inspected event, with the full propagation trace."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from backend.config import get_settings


class Base(DeclarativeBase):
    pass


class EventLog(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(32), unique=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    hop: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String)
    target: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    tier: Mapped[str] = mapped_column(String, index=True)
    trust: Mapped[float] = mapped_column(Float)
    model_trust: Mapped[float | None] = mapped_column(Float, nullable=True)
    features: Mapped[dict] = mapped_column(JSON, default=dict)
    reasons: Mapped[list] = mapped_column(JSON, default=list)
    trace: Mapped[list] = mapped_column(JSON, default=list)
    detector: Mapped[str] = mapped_column(String)
    latency_ms: Mapped[float] = mapped_column(Float)
    preview: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="open")  # quarantine review: open / released / rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        cols = {c.name: getattr(self, c.name) for c in self.__table__.columns}
        cols["created_at"] = self.created_at.isoformat()
        return cols


engine = create_async_engine(get_settings().database_url)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    async with SessionLocal() as session:
        yield session


async def save_verdict(db: AsyncSession, verdict: dict) -> EventLog:
    keys = {c.name for c in EventLog.__table__.columns}
    row = EventLog(**{k: v for k, v in verdict.items() if k in keys})
    db.add(row)
    await db.commit()
    return row


async def tier_counts(db: AsyncSession) -> dict[str, int]:
    rows = await db.execute(select(EventLog.tier, func.count()).group_by(EventLog.tier))
    return {tier: n for tier, n in rows.all()}
