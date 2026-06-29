"""Worker heartbeat persistence helpers."""

from __future__ import annotations

from pathlib import Path

from tradingagents.service.state_backend import get_state_backend_adapter


def write_worker_status(*, path: Path, worker_mode: str) -> None:
    """Write a heartbeat record for a worker process."""
    get_state_backend_adapter().write_worker_status(worker_mode, path=path)


def read_worker_status(*, path: Path, stale_after_seconds: int = 5) -> dict[str, object]:
    """Read heartbeat status and mark stale workers offline."""
    return get_state_backend_adapter().read_worker_status(
        path=path,
        stale_after_seconds=stale_after_seconds,
    )
