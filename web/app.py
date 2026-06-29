"""FastAPI application for TradingAgents Web."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from .auth import get_presented_api_token, get_required_api_token
from .routes import router
from .runner import (
    ensure_worker_started,
    get_execution_mode,
    load_runs_index,
    resume_incomplete_runs,
)

app = FastAPI(
    title="TradingAgents Web",
    description="Multi-Agents LLM Financial Trading Framework - Web Interface",
    version="0.1.0",
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
from pathlib import Path

_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Include API routes
app.include_router(router)


@app.middleware("http")
async def _require_api_token(request, call_next):
    """Optionally protect API endpoints with a shared token."""
    configured = get_required_api_token(request)
    if (
        configured
        and request.url.path.startswith("/api/")
        and get_presented_api_token(request) != configured
    ):
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)
    return await call_next(request)


@app.on_event("startup")
async def _load_persisted_runs() -> None:
    """Restore persisted run history when the app boots."""
    load_runs_index()
    if get_execution_mode() == "local_thread":
        ensure_worker_started()
        resume_incomplete_runs()
