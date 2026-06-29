"""Optional shared-token authentication for the Web API."""

from __future__ import annotations

import os

from fastapi import Request
from tradingagents.service.web_state import get_web_settings_path
from tradingagents.settings import load_settings


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
