"""Helpers for locating persistent state used by the Web runtime."""

from __future__ import annotations

import os
import re
from pathlib import Path

_TENANT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def get_web_state_base_dir() -> Path:
    """Return the shared root directory used for all Web runtime state."""
    override = os.environ.get("TRADINGAGENTS_WEB_STATE_DIR", "").strip()
    if override:
        return Path(override).expanduser()
    return Path.home() / ".tradingagents" / "web"


def normalize_web_tenant_id(tenant_id: str) -> str:
    """Return a tenant namespace safe to use as one filesystem path component."""
    normalized = tenant_id.strip()
    if not _TENANT_ID_RE.fullmatch(normalized):
        raise ValueError(
            "tenant_id must be 1-64 chars using letters, numbers, dot, dash, or underscore"
        )
    return normalized


def get_web_state_dir(tenant_id: str | None = None) -> Path:
    """Return the root directory used for persistent Web runtime state."""
    base = get_web_state_base_dir()
    resolved_tenant_id = get_web_tenant_id(tenant_id)
    if resolved_tenant_id:
        tenants_root = base / "tenants"
        state_dir = tenants_root / resolved_tenant_id
        if not state_dir.resolve().is_relative_to(tenants_root.resolve()):
            raise ValueError("tenant_id resolves outside the tenant state root")
        return state_dir
    return base


def get_web_tenant_id(tenant_id: str | None = None) -> str | None:
    """Return the optional tenant namespace for shared web state."""
    if tenant_id is not None:
        return normalize_web_tenant_id(tenant_id)
    value = os.environ.get("TRADINGAGENTS_WEB_TENANT_ID", "").strip()
    return normalize_web_tenant_id(value) if value else None


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
    tenants_dir = get_web_state_base_dir() / "tenants"
    if not tenants_dir.exists():
        return []
    return sorted(
        entry.name
        for entry in tenants_dir.iterdir()
        if entry.is_dir()
    )
