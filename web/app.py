"""FastAPI application for TradingAgents Web."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .admin_user_routes import router as admin_user_router
from .auth import (
    get_presented_api_token,
    get_request_tenant_id,
    get_required_api_token,
    get_session_user,
    is_user_auth_required,
)
from .auth_routes import router as auth_router
from .permissions import (
    has_required_role,
    is_auth_path,
    is_password_change_allowed_path,
    is_public_path,
    required_role_for_request,
)
from .routes import router
from .runner import (
    ensure_worker_started,
    get_execution_mode,
    load_runs_index,
    resume_incomplete_runs,
)


def _get_cors_origins() -> list[str]:
    configured = os.environ.get("TRADINGAGENTS_WEB_CORS_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]


app = FastAPI(
    title="TradingAgents Web",
    description="Multi-Agents LLM Financial Trading Framework - Web Interface",
    version="0.1.0",
)

# CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
_static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Include API routes
app.include_router(auth_router)
app.include_router(admin_user_router)
app.include_router(router)


@app.middleware("http")
async def _resolve_request_auth(request, call_next):
    """Resolve request auth context for legacy token and browser-session modes."""
    request.state.auth_mode = None
    request.state.current_user = None
    request.state.effective_tenant_id = None

    path = request.url.path
    method = request.method.upper()
    session_user = None
    if path.startswith("/api/"):
        session_user = get_session_user(request)
        if session_user is not None:
            request.state.auth_mode = "session"
            request.state.current_user = session_user
            request.state.effective_tenant_id = session_user.tenant_id

    if is_public_path(path, method):
        return await call_next(request)

    if session_user is not None:
        if session_user.must_change_password and not is_password_change_allowed_path(path, method):
            return JSONResponse(
                {
                    "code": "password_change_required",
                    "detail": "Password change required",
                },
                status_code=403,
            )
        required_role = required_role_for_request(path, method)
        if not has_required_role(session_user.role, required_role):
            return JSONResponse({"detail": "Forbidden"}, status_code=403)
        return await call_next(request)

    if is_auth_path(path, method):
        return await call_next(request)

    try:
        configured = get_required_api_token(request)
    except ValueError as exc:
        return JSONResponse({"detail": str(exc)}, status_code=400)

    if configured:
        if get_presented_api_token(request) != configured:
            return JSONResponse({"detail": "Unauthorized"}, status_code=401)
        request.state.auth_mode = "token"
        request.state.effective_tenant_id = get_request_tenant_id(request)
        return await call_next(request)

    if path.startswith("/api/") and is_user_auth_required():
        return JSONResponse({"detail": "Unauthorized"}, status_code=401)

    if path.startswith("/api/"):
        request.state.auth_mode = "legacy"
        request.state.effective_tenant_id = get_request_tenant_id(request)
    return await call_next(request)


@app.on_event("startup")
async def _load_persisted_runs() -> None:
    """Restore persisted run history when the app boots."""
    load_runs_index()
    if get_execution_mode() == "local_thread":
        ensure_worker_started()
        resume_incomplete_runs()
