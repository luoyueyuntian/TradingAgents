"""Durable event timeline helpers for run execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from tradingagents.service.state_backend import get_state_backend_adapter


def default_event_log_path(run_id: str, *, base_dir: Path) -> Path:
    """Return the default JSONL event log path for a run."""
    return base_dir / f"{run_id}.jsonl"


def load_event_history(
    run_id: str,
    *,
    event_log_path: Path | None = None,
    base_dir: Path | None = None,
) -> tuple[Path, list[dict[str, Any]]]:
    """Load persisted event history for a run."""
    return get_state_backend_adapter().load_events(
        run_id,
        event_log_path=event_log_path,
        base_dir=base_dir or Path.cwd(),
    )


def append_event_record(
    run_id: str,
    event: dict[str, Any],
    *,
    event_log_path: Path | None = None,
    base_dir: Path | None = None,
) -> tuple[Path, dict[str, Any]]:
    """Append one event record to durable history."""
    return get_state_backend_adapter().append_event(
        run_id,
        event,
        event_log_path=event_log_path,
        base_dir=base_dir or Path.cwd(),
    )
