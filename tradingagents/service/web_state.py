"""Helpers for locating persistent state used by the Web runtime."""

from __future__ import annotations

import os
from pathlib import Path


def get_web_state_dir(tenant_id: str | None = None) -> Path:
    """Return the root directory used for persistent Web runtime state."""
    override = os.environ.get("TRADINGAGENTS_WEB_STATE_DIR", "").strip()
    if override:
        base = Path(override).expanduser()
    else:
        base = Path.home() / ".tradingagents" / "web"
    resolved_tenant_id = get_web_tenant_id(tenant_id)
    if resolved_tenant_id:
        return base / "tenants" / resolved_tenant_id
    return base


def get_web_tenant_id(tenant_id: str | None = None) -> str | None:
    """Return the optional tenant namespace for shared web state."""
    if tenant_id:
        return tenant_id
    value = os.environ.get("TRADINGAGENTS_WEB_TENANT_ID", "").strip()
    return value or None


def get_web_state_backend() -> str:
    """Return the configured persistent state backend."""
    backend = os.environ.get("TRADINGAGENTS_WEB_STATE_BACKEND", "file").strip().lower()
    return backend or "file"


def get_web_sqlite_path(tenant_id: str | None = None) -> Path:
    """Return the SQLite database path for the optional SQLite backend."""
    override = os.environ.get("TRADINGAGENTS_WEB_SQLITE_PATH", "").strip()
    if override:
        return Path(override).expanduser()
    return get_web_state_dir(tenant_id) / "state.db"


def get_web_runs_root(tenant_id: str | None = None) -> Path:
    return get_web_state_dir(tenant_id) / "runs"


def get_web_events_dir(tenant_id: str | None = None) -> Path:
    return get_web_state_dir(tenant_id) / "events"


def get_web_runs_index_path(tenant_id: str | None = None) -> Path:
    return get_web_state_dir(tenant_id) / "runs.json"


def get_web_worker_status_path(tenant_id: str | None = None) -> Path:
    return get_web_state_dir(tenant_id) / "worker-status.json"


def get_web_claims_dir(tenant_id: str | None = None) -> Path:
    return get_web_state_dir(tenant_id) / "claims"


def get_web_settings_path(tenant_id: str | None = None) -> Path:
    return get_web_state_dir(tenant_id) / "settings.json"


def list_web_tenant_ids() -> list[str]:
    """Discover tenant namespaces stored under the shared web state root."""
    tenants_dir = (Path.home() / ".tradingagents" / "web") / "tenants"
    if not tenants_dir.exists():
        return []
    return sorted(
        entry.name
        for entry in tenants_dir.iterdir()
        if entry.is_dir()
    )
