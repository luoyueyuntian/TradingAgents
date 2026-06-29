"""Analysis execution bridge: tenant-scoped RunService registry for the Web layer."""

from __future__ import annotations

import os
import threading

from tradingagents.service.models import RunState, TERMINAL_RUN_STATUSES
from tradingagents.service.run_service import RunService
from tradingagents.service.state_backend import get_state_backend_adapter
from tradingagents.service.web_state import (
    get_web_claims_dir,
    get_web_events_dir,
    get_web_runs_index_path,
    get_web_runs_root,
    get_web_settings_path,
    get_web_sqlite_path,
    get_web_state_dir,
    get_web_worker_status_path,
    get_web_tenant_id,
)

from .schemas import AnalysisRequest
from tradingagents.settings import load_settings

_service_lock = threading.Lock()
_services: dict[str, RunService] = {}
_service: RunService | None = None


def get_tenant_id(tenant_id: str | None = None) -> str | None:
    """Resolve the effective tenant id for this request/session."""
    return get_web_tenant_id(tenant_id)


def _build_service(tenant_id: str | None = None) -> RunService:
    resolved = get_tenant_id(tenant_id)
    return RunService(
        tenant_id=resolved,
        runs_index_path=get_web_runs_index_path(resolved),
        run_events_dir=get_web_events_dir(resolved),
        runs_root_dir=get_web_runs_root(resolved),
        worker_status_path=get_web_worker_status_path(resolved),
        claims_dir=get_web_claims_dir(resolved),
    )


_service = _build_service(None)


def get_service(tenant_id: str | None = None) -> RunService:
    """Return the RunService for the resolved tenant namespace."""
    global _service
    resolved = get_tenant_id(tenant_id)
    key = resolved or "__default__"

    if resolved is None:
        with _service_lock:
            return _service

    with _service_lock:
        service = _services.get(key)
        if service is None:
            service = _build_service(resolved)
            _services[key] = service
        return service


def get_execution_mode() -> str:
    """Return the web run execution mode."""
    mode = os.environ.get("TRADINGAGENTS_WEB_RUN_MODE", "local_thread").strip().lower()
    return mode or "local_thread"


def get_state_backend() -> str:
    """Return the configured web state backend."""
    return get_state_backend_adapter().kind


def get_state_location(tenant_id: str | None = None) -> str:
    """Return the primary storage location for the current backend."""
    adapter = get_state_backend_adapter()
    if adapter.kind == "sqlite":
        return str(get_web_sqlite_path(get_tenant_id(tenant_id)))
    return str(get_web_state_dir(get_tenant_id(tenant_id)))


def refresh_from_storage_if_needed(tenant_id: str | None = None) -> None:
    """Reload persisted state when running in external-worker mode."""
    if get_execution_mode() == "external_worker":
        get_service(tenant_id).load_runs_index()


def save_runs_index(tenant_id: str | None = None) -> None:
    get_service(tenant_id).save_runs_index()


def load_runs_index(tenant_id: str | None = None) -> None:
    get_service(tenant_id).load_runs_index()


def resume_incomplete_runs(tenant_id: str | None = None) -> None:
    get_service(tenant_id).resume_incomplete_runs()


def load_run_event_history(run: RunState, tenant_id: str | None = None) -> None:
    get_service(tenant_id).load_run_event_history(run)


def get_run(run_id: str, tenant_id: str | None = None) -> RunState | None:
    refresh_from_storage_if_needed(tenant_id)
    return get_service(tenant_id).get_run(run_id)


def list_runs(tenant_id: str | None = None) -> list[RunState]:
    refresh_from_storage_if_needed(tenant_id)
    return get_service(tenant_id).list_runs()


def get_queue_position(run_id: str, tenant_id: str | None = None) -> int | None:
    refresh_from_storage_if_needed(tenant_id)
    return get_service(tenant_id).get_queue_position(run_id)


def get_service_status(tenant_id: str | None = None) -> dict[str, object]:
    refresh_from_storage_if_needed(tenant_id)
    return get_service(tenant_id).get_status_snapshot()


def subscribe_run_events(run: RunState, tenant_id: str | None = None):
    return get_service(tenant_id).subscribe_run_events(run)


def unsubscribe_run_events(run: RunState, subscriber_id: str, tenant_id: str | None = None) -> None:
    get_service(tenant_id).unsubscribe_run_events(run, subscriber_id)


def build_terminal_event(run: RunState, tenant_id: str | None = None):
    return get_service(tenant_id).build_terminal_event(run)


def prune_terminal_runs(max_completed: int = 100, tenant_id: str | None = None) -> None:
    get_service(tenant_id).prune_terminal_runs(max_completed=max_completed)


def _put_event(run: RunState, event: dict, tenant_id: str | None = None) -> None:
    get_service(tenant_id)._put_event(run, event)


def cancel_run(run_id: str, tenant_id: str | None = None) -> RunState | None:
    refresh_from_storage_if_needed(tenant_id)
    return get_service(tenant_id).cancel_run(run_id)


def delete_run(run_id: str, tenant_id: str | None = None) -> RunState | None:
    refresh_from_storage_if_needed(tenant_id)
    return get_service(tenant_id).delete_run(run_id)


def retry_run(run_id: str, tenant_id: str | None = None) -> RunState | None:
    refresh_from_storage_if_needed(tenant_id)
    return get_service(tenant_id).retry_run(run_id, start_worker=get_execution_mode() != "external_worker")


def ensure_worker_started(tenant_id: str | None = None) -> None:
    get_service(tenant_id).ensure_worker_started()


def create_run(req: AnalysisRequest, _loop=None, tenant_id: str | None = None) -> RunState:
    settings = load_settings(path=get_web_settings_path(get_tenant_id(tenant_id)))
    return get_service(tenant_id).create_run(
        req,
        start_worker=get_execution_mode() != "external_worker",
        settings=settings,
    )


def build_run_request_config(req: AnalysisRequest, *, runtime_context=None, tenant_id: str | None = None, settings: dict | None = None) -> dict:
    return get_service(tenant_id).build_run_request_config(req, runtime_context=runtime_context, settings=settings)
