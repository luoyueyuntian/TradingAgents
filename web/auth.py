"""Optional shared-token authentication for the Web API."""

from __future__ import annotations

import os

from fastapi import Request

from tradingagents.service.web_state import get_web_auth_db_path, get_web_settings_path
from tradingagents.settings import load_settings

from .user_store import UserRecord, UserStore

SESSION_COOKIE_NAME = "tradingagents_session"


def get_configured_api_token() -> str | None:
    """Return the configured API token, if auth is enabled."""
    value = os.environ.get("TRADINGAGENTS_WEB_API_TOKEN", "").strip()
    return value or None


def get_required_api_token(request: Request) -> str | None:
    """Return the token required for this request, preferring tenant settings."""
    tenant_id = request.headers.get("X-TradingAgents-Tenant") or request.query_params.get("tenant_id") or None
    tenant_settings = load_settings(path=get_web_settings_path(tenant_id))
    tenant_token = str(tenant_settings.get("security", {}).get("web_api_token", "")).strip()
    if tenant_token:
        return tenant_token
    return get_configured_api_token()


def get_auth_scope(tenant_id: str | None = None) -> str:
    """Describe whether auth is tenant-scoped, global, or disabled."""
    tenant_settings = load_settings(path=get_web_settings_path(tenant_id))
    tenant_token = str(tenant_settings.get("security", {}).get("web_api_token", "")).strip()
    if tenant_token:
        return "tenant"
    if get_configured_api_token():
        return "global"
    return "disabled"


def get_presented_api_token(request: Request) -> str | None:
    """Extract a presented API token from query params or headers."""
    query_token = request.query_params.get("api_token", "").strip()
    if query_token:
        return query_token

    header_token = request.headers.get("X-TradingAgents-Token", "").strip()
    if header_token:
        return header_token

    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        return token or None

    return None


def _user_bootstrap_configured() -> bool:
    return all(
        os.environ.get(env_var, "").strip()
        for env_var in (
            "TRADINGAGENTS_ADMIN_EMAIL",
            "TRADINGAGENTS_ADMIN_PASSWORD",
            "TRADINGAGENTS_ADMIN_TENANT_ID",
        )
    )


def is_user_auth_required() -> bool:
    store = UserStore(get_web_auth_db_path())
    return store.count_users() > 0 or _user_bootstrap_configured()


def get_session_user(request: Request) -> UserRecord | None:
    raw_session_id = request.cookies.get(SESSION_COOKIE_NAME, "").strip()
    if not raw_session_id:
        return None
    store = UserStore(get_web_auth_db_path())
    session = store.get_session(raw_session_id)
    if session is None:
        return None
    return store.get_user(session.user_id)


def get_request_user(request: Request) -> UserRecord | None:
    return getattr(request.state, "current_user", None)


def get_request_tenant_id(request: Request) -> str | None:
    user = get_request_user(request)
    if user is not None:
        return user.tenant_id
    return request.headers.get("X-TradingAgents-Tenant") or request.query_params.get("tenant_id") or None
