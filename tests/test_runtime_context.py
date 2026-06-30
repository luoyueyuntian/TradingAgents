"""Tests for runtime context paths used by the web runtime."""

from __future__ import annotations

from pathlib import Path

from tradingagents.service.runtime_context import build_runtime_context


def test_build_runtime_context_isolates_paths_per_run(tmp_path):
    context = build_runtime_context("run-123", base_dir=tmp_path / "runs")

    assert context.run_root == tmp_path / "runs" / "run-123"
    assert context.results_dir == tmp_path / "runs" / "run-123" / "results"
    assert context.cache_dir == tmp_path / "cache"
    assert context.memory_log_path == tmp_path / "memory" / "trading_memory.md"
    assert isinstance(context.run_root, Path)
