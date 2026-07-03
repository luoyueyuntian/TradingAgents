"""File-based run claim helpers for cross-process worker coordination."""

from __future__ import annotations

from pathlib import Path

from tradingagents.service.state_backend import get_state_backend_adapter


def claim_path(run_id: str, *, claims_dir: Path) -> Path:
    return claims_dir / f"{run_id}.lock"


def acquire_run_claim(run_id: str, *, claims_dir: Path) -> Path | None:
    """Acquire an exclusive claim for one run, or return None if already claimed."""
    return get_state_backend_adapter().acquire_claim(run_id, claims_dir=claims_dir)


def release_run_claim(path: Path) -> None:
    """Release a previously acquired run claim."""
    get_state_backend_adapter().release_claim(path)
