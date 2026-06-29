"""Run-scoped filesystem context for Web and worker execution."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tradingagents.service.web_state import get_web_runs_root


@dataclass(frozen=True)
class RuntimeContext:
    """Immutable run-scoped storage paths."""

    run_id: str
    run_root: Path
    results_dir: Path
    cache_dir: Path
    memory_log_path: Path


def build_runtime_context(
    run_id: str,
    *,
    base_dir: Path | None = None,
) -> RuntimeContext:
    """Build a filesystem context isolated to one run."""
    root = (base_dir or get_web_runs_root()) / run_id
    return RuntimeContext(
        run_id=run_id,
        run_root=root,
        results_dir=root / "results",
        cache_dir=root / "cache",
        memory_log_path=root / "memory" / "trading_memory.md",
    )
