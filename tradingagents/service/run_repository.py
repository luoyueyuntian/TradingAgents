"""Persistence wrappers for run index storage."""

from __future__ import annotations

from pathlib import Path

from tradingagents.service.models import RunState
from tradingagents.service.run_state_codec import deserialize_run_state, serialize_run_state
from tradingagents.service.state_backend import get_state_backend_adapter, index_lock_path


def save_runs_to_index(runs: list[RunState], *, index_path: Path) -> None:
    """Persist runs to the active backend, newest first."""
    get_state_backend_adapter().save_runs(runs, index_path=index_path)


def upsert_run_in_index(run: RunState, *, index_path: Path) -> None:
    """Insert or replace one run entry while preserving others."""
    get_state_backend_adapter().upsert_run(run, index_path=index_path)


def delete_run_from_index(run_id: str, *, index_path: Path) -> None:
    """Remove one run entry from the active backend."""
    get_state_backend_adapter().delete_run(run_id, index_path=index_path)


def load_runs_from_index(*, index_path: Path, runs_root_dir: Path) -> dict[str, RunState]:
    """Load runs from the active backend."""
    return get_state_backend_adapter().load_runs(
        runs_root_dir=runs_root_dir,
        index_path=index_path,
    )


__all__ = [
    "deserialize_run_state",
    "delete_run_from_index",
    "index_lock_path",
    "load_runs_from_index",
    "save_runs_to_index",
    "serialize_run_state",
    "upsert_run_in_index",
]
