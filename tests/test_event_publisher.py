"""Tests for durable run event publishing helpers."""

from __future__ import annotations

from tradingagents.service.event_publisher import append_event_record, load_event_history


def test_append_event_record_and_load_event_history_round_trip(tmp_path):
    path, record = append_event_record(
        "run-1",
        {"event": "progress", "data": {"message": "hello"}},
        base_dir=tmp_path,
    )

    loaded_path, history = load_event_history("run-1", base_dir=tmp_path)

    assert path == loaded_path
    assert record["event"] == "progress"
    assert history == [record]


def test_load_event_history_skips_malformed_lines(tmp_path):
    event_log = tmp_path / "run-1.jsonl"
    event_log.write_text('{"event":"progress","data":{}}\nnot-json\n', encoding="utf-8")

    _, history = load_event_history("run-1", event_log_path=event_log)

    assert len(history) == 1
    assert history[0]["event"] == "progress"
