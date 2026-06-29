"""Tests for run artifact discovery and resolution."""

from __future__ import annotations

from tradingagents.service.artifact_store import (
    build_run_artifacts,
    delete_run_artifacts,
    resolve_run_artifact,
)


def test_build_run_artifacts_lists_report_tree_and_full_state(tmp_path):
    report_root = tmp_path / "reports"
    report_root.mkdir()
    complete = report_root / "complete_report.md"
    complete.write_text("# Complete\n", encoding="utf-8")
    market = report_root / "1_analysts" / "market.md"
    market.parent.mkdir()
    market.write_text("market", encoding="utf-8")
    research = report_root / "2_research" / "manager.md"
    research.parent.mkdir()
    research.write_text("research", encoding="utf-8")
    full_state = tmp_path / "full_state.json"
    full_state.write_text("{}", encoding="utf-8")

    artifacts = build_run_artifacts(
        report_path=str(complete),
        state_log_path=str(full_state),
    )

    assert [artifact.key for artifact in artifacts] == [
        "complete-report",
        "full-state",
        "report-tree/1_analysts/market.md",
        "report-tree/2_research/manager.md",
    ]


def test_resolve_run_artifact_supports_report_tree_and_legacy_keys(tmp_path):
    report_root = tmp_path / "reports"
    report_root.mkdir()
    complete = report_root / "complete_report.md"
    complete.write_text("# Complete\n", encoding="utf-8")
    market = report_root / "1_analysts" / "market.md"
    market.parent.mkdir()
    market.write_text("market", encoding="utf-8")
    full_state = tmp_path / "full_state.json"
    full_state.write_text("{}", encoding="utf-8")

    resolved_complete = resolve_run_artifact(
        report_path=str(complete),
        state_log_path=str(full_state),
        key="complete-report",
    )
    resolved_tree = resolve_run_artifact(
        report_path=str(complete),
        state_log_path=str(full_state),
        key="report-tree/1_analysts/market.md",
    )
    resolved_state = resolve_run_artifact(
        report_path=str(complete),
        state_log_path=str(full_state),
        key="full-state",
    )

    assert resolved_complete is not None and resolved_complete.path == complete
    assert resolved_tree is not None and resolved_tree.path == market
    assert resolved_state is not None and resolved_state.path == full_state


def test_delete_run_artifacts_removes_run_root_and_event_log(tmp_path):
    run_root = tmp_path / "runs" / "run-1"
    report_file = run_root / "results" / "complete_report.md"
    report_file.parent.mkdir(parents=True)
    report_file.write_text("report", encoding="utf-8")
    event_log = tmp_path / "events" / "run-1.jsonl"
    event_log.parent.mkdir(parents=True)
    event_log.write_text("{}", encoding="utf-8")

    delete_run_artifacts(run_root=run_root, event_log_path=str(event_log))

    assert not run_root.exists()
    assert not event_log.exists()
