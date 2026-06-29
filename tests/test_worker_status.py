"""Tests for worker heartbeat helpers."""

from __future__ import annotations

from pathlib import Path

from tradingagents.service.worker_status import read_worker_status, write_worker_status


def test_write_and_read_worker_status_round_trip(tmp_path):
    path = tmp_path / "worker-status.json"
    write_worker_status(path=path, worker_mode="external_worker")

    status = read_worker_status(path=path, stale_after_seconds=30)

    assert status["worker_running"] is True
    assert status["worker_mode"] == "external_worker"
    assert "last_seen" in status


def test_read_worker_status_marks_stale_heartbeat_offline(tmp_path):
    path = tmp_path / "worker-status.json"
    path.write_text('{"worker_mode":"external_worker","last_seen":"2000-01-01T00:00:00"}', encoding="utf-8")

    status = read_worker_status(path=path, stale_after_seconds=1)

    assert status["worker_running"] is False
