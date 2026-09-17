"""
MAPIS Database Models
=====================
SQLAlchemy async models for persistent alert/event logging.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from backend.config import settings

Base = declarative_base()

engine = create_async_engine(settings.DATABASE_URL, echo=False)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class AlertLog(Base):
    """Persistent log of all BLOCK and WARN events."""
    __tablename__ = "alert_logs"

    id           = Column(Integer, primary_key=True, index=True)
    session_id   = Column(String, index=True, nullable=False)
    source_agent = Column(String, nullable=False)
    target_agent = Column(String, nullable=False)
    decision     = Column(String, nullable=False)        # BLOCK / WARN
    final_score  = Column(Float, nullable=False)
    pattern_hits = Column(JSON, default=[])
    explanation  = Column(Text, nullable=False)
    timestamp    = Column(DateTime, default=datetime.utcnow)


class MessageLog(Base):
    """Full message log for forensic analysis / audit trail."""
    __tablename__ = "message_logs"

    id            = Column(Integer, primary_key=True, index=True)
    session_id    = Column(String, index=True, nullable=False)
    source_agent  = Column(String, nullable=False)
    target_agent  = Column(String, nullable=False)
    message_hash  = Column(String, nullable=False)
    raw_score     = Column(Float, nullable=False)
    final_score   = Column(Float, nullable=False)
    session_penalty = Column(Float, default=0.0)
    decision      = Column(String, nullable=False)
    explanation   = Column(Text)
    timestamp     = Column(DateTime, default=datetime.utcnow)


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """FastAPI dependency: yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session
