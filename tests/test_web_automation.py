"""Tests for scheduled automation helpers."""

from __future__ import annotations

import datetime
from types import SimpleNamespace

from web import automation as web_automation
from web.schemas import AutomationAnalysisConfig, AutomationRuleCreate


def test_create_and_list_automation_rules_compute_next_run(monkeypatch):
    state: dict[str, object] = {}

    monkeypatch.setattr(web_automation, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_automation, "save_settings", lambda settings, path=None: state.update(settings))

    created = web_automation.create_automation_rule(
        AutomationRuleCreate(
            name="Morning Sweep",
            source="watchlist",
            cadence="daily",
            time_of_day="09:15",
            analysis_config=AutomationAnalysisConfig(
                analysts=["market"],
                llm_provider="openai",
                quick_think_model="gpt-5.4-mini",
                deep_think_model="gpt-5.5",
                research_depth=3,
                output_language="English",
            ),
        ),
        now=datetime.datetime(2026, 1, 15, 8, 0, 0),
    )
    listed = web_automation.list_automation_rules(now=datetime.datetime(2026, 1, 15, 8, 0, 0))

    assert created.name == "Morning Sweep"
    assert listed[0].next_run_at == "2026-01-15T09:15:00"
    assert state["automations"]["items"][0]["name"] == "Morning Sweep"


def test_process_due_automation_rules_queues_watchlist_once_per_slot(monkeypatch):
    state = {
        "watchlist": {"tickers": [{"ticker": "NVDA"}, {"ticker": "MSFT"}]},
        "automations": {
            "items": [
                {
                    "id": "auto-1",
                    "name": "Daily Watchlist",
                    "enabled": True,
                    "source": "watchlist",
                    "tickers": [],
                    "cadence": "daily",
                    "time_of_day": "09:00",
                    "created_at": "2026-01-15T08:00:00",
                    "updated_at": "2026-01-15T08:00:00",
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                }
            ]
        },
    }
    created = []

    class FakeService:
        def load_tenant_settings(self):
            return {}

        def create_run(self, req, *, start_worker=True, settings=None):
            created.append(req)
            return SimpleNamespace(
                run_id=f"{req.ticker.lower()}-{len(created)}",
                status="queued",
                ticker=req.ticker,
                date=req.date,
            )

    monkeypatch.setattr(web_automation, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_automation, "save_settings", lambda settings, path=None: state.update(settings))
    monkeypatch.setattr(web_automation, "get_service", lambda tenant_id=None: FakeService())

    now = datetime.datetime(2026, 1, 15, 9, 30, 0)
    first = web_automation.process_due_automation_rules(now=now, start_worker=False)
    second = web_automation.process_due_automation_rules(now=now, start_worker=False)

    assert first == 2
    assert second == 0
    assert [req.ticker for req in created] == ["NVDA", "MSFT"]
    assert state["automations"]["items"][0]["last_queued_count"] == 2
    assert state["automations"]["items"][0]["last_triggered_at"] == "2026-01-15T09:30:00"


def test_run_automation_rule_now_returns_created_runs_for_manual_tickers(monkeypatch):
    state = {
        "automations": {
            "items": [
                {
                    "id": "auto-1",
                    "name": "Manual Basket",
                    "enabled": True,
                    "source": "manual",
                    "tickers": ["NVDA", "BTC-USD"],
                    "cadence": "weekly",
                    "weekday": "fri",
                    "time_of_day": "10:00",
                    "created_at": "2026-01-15T08:00:00",
                    "updated_at": "2026-01-15T08:00:00",
                    "analysis_config": {
                        "analysts": ["market", "news"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 3,
                        "output_language": "English",
                    },
                }
            ]
        },
    }
    created = []

    class FakeService:
        def load_tenant_settings(self):
            return {}

        def create_run(self, req, *, start_worker=True, settings=None):
            created.append(req)
            return SimpleNamespace(
                run_id=f"{req.ticker.lower()}-{len(created)}",
                status="queued",
                ticker=req.ticker,
                date=req.date,
            )

    monkeypatch.setattr(web_automation, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_automation, "save_settings", lambda settings, path=None: state.update(settings))
    monkeypatch.setattr(web_automation, "get_service", lambda tenant_id=None: FakeService())

    response = web_automation.run_automation_rule_now(
        "auto-1",
        now=datetime.datetime(2026, 1, 16, 10, 5, 0),
        start_worker=False,
    )

    assert response is not None
    assert response.created_count == 2
    assert response.tickers == ["NVDA", "BTC-USD"]
    assert [req.asset_type for req in created] == ["stock", "crypto"]
