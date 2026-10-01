"""MAPIS — Multi-Agent Prompt Injection Shield (FastAPI entry point)."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from backend.api.routes import router
from backend.config import get_settings
from backend.core.shield import MapisShield
from backend.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    app.state.shield = getattr(app.state, "shield", None) or MapisShield()
    s = app.state.shield
    logger.info(f"MAPIS ready — detector={s.detector.name} store={s.store.kind} fail_mode={s.cfg.fail_mode}")
    yield


app = FastAPI(title="MAPIS", version="2.0.0", lifespan=lifespan,
              description="Stateful trust-scoring shield for multi-agent LLM pipelines (indirect prompt injection).")
cfg = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=[cfg.frontend_url, "http://localhost:3000", "http://localhost:5173"],
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(router, prefix="/api/v1")
