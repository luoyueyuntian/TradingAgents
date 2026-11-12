"""Tests for run-scoped LLM usage aggregation."""

from __future__ import annotations

from types import SimpleNamespace

from tradingagents.service.usage_tracking import RunUsageTracker


def _response(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
):
    message = SimpleNamespace(
        usage_metadata={
            "input_tokens": prompt_tokens,
            "output_tokens": completion_tokens,
            "total_tokens": total_tokens,
        },
        response_metadata={"model_name": model},
    )
    generation = SimpleNamespace(message=message)
    return SimpleNamespace(
        llm_output={},
        generations=[[generation]],
    )


def test_usage_tracker_aggregates_calls_and_tokens() -> None:
    events: list[dict[str, object]] = []
    tracker = RunUsageTracker(provider="openai", event_sink=events.append)

    tracker.on_chat_model_start(
        {"name": "chat-openai"},
        [[SimpleNamespace(type="human", content="Summarize AAPL price action.")]],
        invocation_params={"model": "gpt-5.5"},
    )
    tracker.on_llm_end(_response(model="gpt-5.5", prompt_tokens=80, completion_tokens=20, total_tokens=100))
    tracker.on_llm_end(_response(model="gpt-5.4-mini", prompt_tokens=40, completion_tokens=10, total_tokens=50))

    snapshot = tracker.snapshot()
    assert snapshot["provider"] == "openai"
    assert snapshot["total_calls"] == 2
    assert snapshot["prompt_tokens"] == 120
    assert snapshot["completion_tokens"] == 30
    assert snapshot["total_tokens"] == 150
    assert snapshot["calls_by_model"]["gpt-5.5"] == 1
    assert snapshot["tokens_by_model"]["gpt-5.4-mini"]["total_tokens"] == 50
    assert events[0]["model"] == "gpt-5.5"
    assert "Summarize AAPL price action." in str(events[0]["prompt_preview"])
    assert "response_preview" in events[1]
    assert events[2]["total_tokens"] == 50
