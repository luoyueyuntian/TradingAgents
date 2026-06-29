"""Shared serialization helpers for persisted run state."""

from __future__ import annotations

from pathlib import Path

from tradingagents.default_config import build_default_config
from tradingagents.service.models import RunState
from tradingagents.service.runtime_context import build_runtime_context


def serialize_run_state(run: RunState) -> dict:
    """Serialize a run state to JSON-safe metadata."""
    return {
        "run_id": run.run_id,
        "ticker": run.ticker,
        "date": run.date,
        "asset_type": run.asset_type,
        "config": run.config,
        "selected_analysts": list(run.selected_analysts),
        "run_root": str(run.runtime_context.run_root),
        "status": run.status,
        "agents": dict(run.agents),
        "report_sections": dict(run.report_sections),
        "current_report": run.current_report,
        "final_report": run.final_report,
        "signal": run.signal,
        "error": run.error,
        "report_path": run.report_path,
        "state_log_path": run.state_log_path,
        "event_log_path": run.event_log_path,
        "queue_sequence": run.queue_sequence,
        "created_at": run.created_at,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
    }


def deserialize_run_state(payload: dict, *, runs_root_dir: Path) -> RunState:
    """Rebuild one run state from persisted metadata."""
    run_root = payload.get("run_root")
    runtime_context = build_runtime_context(
        payload["run_id"],
        base_dir=Path(run_root).parent if run_root else runs_root_dir,
    )

    run = RunState(
        run_id=payload["run_id"],
        ticker=payload["ticker"],
        date=payload["date"],
        asset_type=payload.get("asset_type", "stock"),
        config=payload.get("config") or build_default_config(),
        selected_analysts=payload.get("selected_analysts") or ["market", "social", "news", "fundamentals"],
        runtime_context=runtime_context,
        status=payload.get("status", "pending"),
        current_report=payload.get("current_report"),
        final_report=payload.get("final_report"),
        signal=payload.get("signal"),
        error=payload.get("error"),
        report_path=payload.get("report_path"),
        state_log_path=payload.get("state_log_path"),
        event_log_path=payload.get("event_log_path"),
        queue_sequence=payload.get("queue_sequence"),
        created_at=payload.get("created_at", ""),
        started_at=payload.get("started_at"),
        completed_at=payload.get("completed_at"),
    )
    run.agents.update(payload.get("agents") or {})
    run.report_sections.update(payload.get("report_sections") or {})
    return run
