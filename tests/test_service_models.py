"""Tests for service-layer run models."""

from __future__ import annotations

import asyncio

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.service.models import TERMINAL_RUN_STATUSES, RunState
from tradingagents.service.runtime_context import build_runtime_context


def test_run_state_initializes_agent_and_report_maps():
    run = RunState(
        run_id="run-1",
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market", "news"],
        runtime_context=build_runtime_context("run-1"),
    )

    assert "Market Analyst" in run.agents
    assert "News Analyst" in run.agents
    assert "Sentiment Analyst" not in run.agents
    assert "market_report" in run.report_sections
    assert "news_report" in run.report_sections
    assert "sentiment_report" not in run.report_sections


def test_run_state_event_subscription_round_trip():
    async def exercise():
        run = RunState(
            run_id="run-2",
            ticker="AAPL",
            date="2026-01-15",
            asset_type="stock",
            config=DEFAULT_CONFIG.copy(),
            selected_analysts=["market"],
            runtime_context=build_runtime_context("run-2"),
        )

        sub_id, queue = run.subscribe_events()
        subscribers = run.snapshot_event_subscribers()

        assert sub_id
        assert len(subscribers) == 1
        assert subscribers[0][1] is queue

        run.unsubscribe_events(sub_id)

        assert run.snapshot_event_subscribers() == []

    asyncio.run(exercise())


def test_terminal_run_statuses_include_cancelled():
    assert {"completed", "failed", "cancelled"} <= TERMINAL_RUN_STATUSES
