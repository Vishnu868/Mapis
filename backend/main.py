"""
MAPIS — Multi-Agent Prompt Injection Shield
============================================
FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.config import settings
from backend.models.database import init_db
from backend.api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("=" * 50)
    logger.info("  MAPIS — Multi-Agent Prompt Injection Shield")
    logger.info("  Starting up...")
    logger.info("=" * 50)
    await init_db()
    logger.info("✅ Database initialized")
    logger.info(f"✅ Trust block threshold: {settings.TRUST_BLOCK_THRESHOLD}")
    logger.info(f"✅ Trust warn threshold:  {settings.TRUST_WARN_THRESHOLD}")
    logger.info("✅ MAPIS is ready to protect your agent pipelines")
    yield
    logger.info("MAPIS shutting down...")


app = FastAPI(
    title="MAPIS — Multi-Agent Prompt Injection Shield",
    description=(
        "Real-time stateful defense system that protects multi-agent LLM pipelines "
        "from indirect prompt injection attacks spanning multiple agent hops."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "service": "MAPIS",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }
