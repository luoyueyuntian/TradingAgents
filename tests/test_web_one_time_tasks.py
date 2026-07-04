"""Tests for one-time analysis task schemas."""

from __future__ import annotations

import datetime
from copy import deepcopy
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from web import one_time_tasks as task_module
from web.schemas import (
    AutomationAnalysisConfig,
    ManualStockSelection,
    OneTimeTask,
    OneTimeTaskCreate,
    OneTimeTaskPage,
    OneTimeTaskSelectionSnapshot,
    OneTimeTaskUpdate,
    StockGroup,
    StockGroupCreate,
    StockGroupUpdate,
)


def test_stock_group_create_normalizes_name_and_tickers():
    group = StockGroupCreate(name="  AI Leaders  ", tickers=[" nvda ", "msft", "NVDA", "  ", "aapl"])

    assert group.name == "AI Leaders"
    assert group.tickers == ["NVDA", "MSFT", "AAPL"]


def test_stock_group_update_normalizes_name_and_tickers():
    group = StockGroupUpdate(name="  Core Basket  ", tickers=[" nvda ", "MSFT", "nvda", "aapl "])

    assert group.name == "Core Basket"
    assert group.tickers == ["NVDA", "MSFT", "AAPL"]


def test_stock_group_saved_model_rejects_empty_ticker_list():
    with pytest.raises(ValidationError, match="tickers.*must not be empty"):
        StockGroup(id="group-1", name="AI Leaders", tickers=[], created_at="2026-07-01T12:00:00", updated_at="2026-07-01T12:00:00")


def test_stock_group_saved_model_rejects_omitted_tickers():
    with pytest.raises(ValidationError, match="Field required"):
        StockGroup(id="group-1", name="AI Leaders", created_at="2026-07-01T12:00:00", updated_at="2026-07-01T12:00:00")


def test_stock_group_create_rejects_blank_name():
    with pytest.raises(ValidationError, match="name.*must not be blank"):
        StockGroupCreate(name="   ", tickers=["NVDA"])


def test_manual_stock_selection_accepts_minimal_shape():
    stock = ManualStockSelection(market="  CN_A ", symbol=" 600519.sh ")

    assert stock.market == "cn_a"
    assert stock.symbol == "600519.SH"
    assert stock.name is None
    assert stock.exchange is None


def test_manual_stock_selection_normalizes_optional_metadata():
    stock = ManualStockSelection(
        market="  CN_A ",
        symbol=" 600519.sh ",
        name=" 贵州茅台 ",
        exchange=" sse ",
    )

    assert stock.market == "cn_a"
    assert stock.symbol == "600519.SH"
    assert stock.name == "贵州茅台"
    assert stock.exchange == "sse"


def test_manual_stock_selection_rejects_unknown_market():
    with pytest.raises(ValidationError, match="market.*cn_a.*hk.*us"):
        ManualStockSelection(market="crypto", symbol="BTC-USD")


def test_one_time_task_selection_snapshot_rejects_missing_or_empty_resolved_tickers():
    with pytest.raises(ValidationError, match="resolved_tickers\n  Field required"):
        OneTimeTaskSelectionSnapshot(
            manual_stocks=[],
            group_snapshots=[],
            include_watchlist=False,
        )

    with pytest.raises(ValidationError, match="resolved_tickers.*must not be empty"):
        OneTimeTaskSelectionSnapshot(
            manual_stocks=[],
            group_snapshots=[],
            include_watchlist=False,
            resolved_tickers=[],
        )


def test_one_time_task_shared_models_round_trip():
    snapshot = OneTimeTaskSelectionSnapshot(
        manual_stocks=[ManualStockSelection(market="cn_a", symbol="600519.sh", name="贵州茅台", exchange="SSE")],
        group_snapshots=[{"id": "group-1", "name": "AI Leaders", "tickers": ["NVDA", "MSFT"]}],
        include_watchlist=True,
        watchlist_snapshot=["AAPL", "0700.hk", "AAPL"],
        resolved_tickers=["600519.SH", "NVDA", "MSFT", "AAPL", "0700.HK"],
    )
    task = OneTimeTask(
        id="task-1",
        name="  Friday Basket  ",
        status="scheduled",
        scheduled_for="2026-07-10 21:30",
        analysis_date="2026-07-10",
        selection_snapshot=snapshot,
        analysis_config=AutomationAnalysisConfig(
            analysts=["market", "news"],
            llm_provider="openai",
            research_depth=3,
            output_language="Chinese",
        ),
        created_at="2026-07-01T12:00:00",
        updated_at="2026-07-01T12:00:00",
        triggered_at=None,
        completed_at=None,
        last_error=None,
        last_queued_count=0,
        run_ids=["run-1", "run-2"],
    )
    page = OneTimeTaskPage(items=[task], page=1, page_size=20, total_count=1)

    assert task.name == "Friday Basket"
    assert task.status == "scheduled"
    assert task.selection_snapshot.resolved_tickers == ["600519.SH", "NVDA", "MSFT", "AAPL", "0700.HK"]
    assert page.items[0].id == "task-1"
    assert page.total_count == 1


def test_one_time_task_update_normalizes_selection_and_validates_dates():
    task = OneTimeTaskUpdate(
        name="  Friday Basket  ",
        scheduled_for="2026-07-10 21:30",
        analysis_date="2026-07-10",
        manual_stocks=[
            {"market": "cn_a", "symbol": " 600519.sh ", "name": "贵州茅台", "exchange": "SSE"},
            {"market": "hk", "symbol": "0700.hk", "name": "腾讯控股", "exchange": "HKEX"},
        ],
        group_ids=["group-1", "group-2", "group-1", "group-3", "group-2"],
        include_watchlist=True,
        analysis_config=AutomationAnalysisConfig(
            analysts=["market", "news"],
            llm_provider="openai",
            research_depth=3,
            output_language="Chinese",
        ),
    )

    assert task.name == "Friday Basket"
    assert task.scheduled_for == "2026-07-10 21:30"
    assert task.analysis_date == "2026-07-10"
    assert task.group_ids == ["group-1", "group-2", "group-3"]
    assert [stock.symbol for stock in task.manual_stocks] == ["600519.SH", "0700.HK"]
    assert [stock.market for stock in task.manual_stocks] == ["cn_a", "hk"]
    assert task.include_watchlist is True


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"scheduled_for": "2026-07-10"}, "scheduled_for must be in YYYY-MM-DD HH:MM format"),
        ({"scheduled_for": "2026-7-10 21:30"}, "scheduled_for must be in YYYY-MM-DD HH:MM format"),
        ({"scheduled_for": "2026-07-10 2:30"}, "scheduled_for must be in YYYY-MM-DD HH:MM format"),
        ({"analysis_date": "2026/07/10"}, "analysis_date must be in YYYY-MM-DD format"),
        ({"analysis_date": "2026-7-10"}, "analysis_date must be in YYYY-MM-DD format"),
    ],
)
def test_one_time_task_create_rejects_invalid_date_formats(kwargs, message):
    base_kwargs = dict(
        name="Friday Basket",
        scheduled_for="2026-07-10 21:30",
        analysis_date="2026-07-10",
        manual_stocks=[],
        group_ids=[],
        analysis_config=AutomationAnalysisConfig(
            analysts=["market"],
            llm_provider="openai",
            research_depth=1,
            output_language="English",
        ),
    )
    base_kwargs.update(kwargs)

    with pytest.raises(ValidationError, match=message):
        OneTimeTaskCreate(**base_kwargs)


def test_create_one_time_task_freezes_manual_groups_and_watchlist(monkeypatch):
    groups = [
        StockGroup(
            id="group-1",
            name="AI Leaders",
            tickers=["NVDA", "MSFT"],
            created_at="2026-07-04T10:00:00",
            updated_at="2026-07-04T10:00:00",
        )
    ]
    state = {"watchlist": {"tickers": [{"ticker": "AAPL"}, {"ticker": "0700.HK"}]}}

    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: state.update(settings))
    monkeypatch.setattr(task_module, "list_stock_groups", lambda tenant_id=None: groups)

    task = task_module.create_one_time_task(
        OneTimeTaskCreate(
            name=" Night task ",
            scheduled_for="2026-07-10 21:30",
            analysis_date="2026-07-11",
            manual_stocks=[{"market": "us", "symbol": " AAPL ", "name": "Apple Inc.", "exchange": "NASDAQ"}],
            group_ids=["group-1"],
            include_watchlist=True,
            analysis_config=AutomationAnalysisConfig(
                analysts=["market"],
                llm_provider="openai",
                quick_think_model="gpt-5.4-mini",
                deep_think_model="gpt-5.5",
                research_depth=1,
                output_language="English",
            ),
        ),
        now=datetime.datetime(2026, 7, 4, 10, 0, 0),
    )

    groups[0].tickers.append("TSLA")

    assert task.name == "Night task"
    assert task.status == "scheduled"
    assert task.selection_snapshot.manual_stocks[0].symbol == "AAPL"
    assert task.selection_snapshot.group_snapshots[0].tickers == ["NVDA", "MSFT"]
    assert task.selection_snapshot.watchlist_snapshot == ["AAPL", "0700.HK"]
    assert task.selection_snapshot.resolved_tickers == ["AAPL", "NVDA", "MSFT", "0700.HK"]


def test_create_one_time_task_persists_snapshot_and_preserves_unrelated_settings(monkeypatch):
    state = {
        "one_time_tasks": {"items": []},
        "watchlist": {"tickers": [{"ticker": "AAPL"}, {"ticker": "0700.HK"}]},
        "unrelated": {"keep": True},
    }
    saved: list[dict[str, object]] = []

    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: saved.append(deepcopy(settings)))
    monkeypatch.setattr(
        task_module,
        "list_stock_groups",
        lambda tenant_id=None: [
            StockGroup(
                id="group-1",
                name="AI Leaders",
                tickers=["NVDA", "MSFT"],
                created_at="2026-07-04T10:00:00",
                updated_at="2026-07-04T10:00:00",
            )
        ],
    )

    task = task_module.create_one_time_task(
        OneTimeTaskCreate(
            name="Night task",
            scheduled_for="2026-07-10 21:30",
            analysis_date="2026-07-11",
            manual_stocks=[{"market": "us", "symbol": "AAPL", "name": "Apple Inc.", "exchange": "NASDAQ"}],
            group_ids=["group-1"],
            include_watchlist=True,
            analysis_config=AutomationAnalysisConfig(
                analysts=["market"],
                llm_provider="openai",
                quick_think_model="gpt-5.4-mini",
                deep_think_model="gpt-5.5",
                research_depth=1,
                output_language="English",
            ),
        ),
        now=datetime.datetime(2026, 7, 4, 10, 0, 0),
    )

    assert saved and len(saved) == 1
    assert saved[0]["unrelated"] == {"keep": True}
    assert saved[0]["one_time_tasks"]["items"][0]["id"] == task.id
    assert saved[0]["one_time_tasks"]["items"][0]["status"] == "scheduled"
    assert saved[0]["one_time_tasks"]["items"][0]["selection_snapshot"]["resolved_tickers"] == [
        "AAPL",
        "NVDA",
        "MSFT",
        "0700.HK",
    ]


def test_create_one_time_task_rejects_empty_resolved_tickers(monkeypatch):
    state = {"one_time_tasks": {"items": []}, "unrelated": {"keep": True}}
    saved: list[dict[str, object]] = []
    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: saved.append(deepcopy(settings)))
    monkeypatch.setattr(task_module, "list_stock_groups", lambda tenant_id=None: [])

    payload = OneTimeTaskCreate(
        name="Empty basket",
        scheduled_for="2026-07-10 21:30",
        analysis_date="2026-07-11",
        manual_stocks=[],
        group_ids=[],
        include_watchlist=False,
        analysis_config=AutomationAnalysisConfig(
            analysts=["market"],
            llm_provider="openai",
            quick_think_model="gpt-5.4-mini",
            deep_think_model="gpt-5.5",
            research_depth=1,
            output_language="English",
        ),
    )

    with pytest.raises(ValueError, match="resolved ticker set must not be empty"):
        task_module.create_one_time_task(payload, now=datetime.datetime(2026, 7, 4, 10, 0, 0))
    assert saved == []


def test_update_one_time_task_persists_rebuilt_snapshot_and_updated_fields(monkeypatch):
    state = {
        "one_time_tasks": {
            "items": [
                {
                    "id": "task-1",
                    "name": "Editable",
                    "status": "completed",
                    "scheduled_for": "2026-07-10 21:30",
                    "analysis_date": "2026-07-10",
                    "selection_snapshot": {
                        "manual_stocks": [{"market": "us", "symbol": "AAPL"}],
                        "group_snapshots": [],
                        "include_watchlist": False,
                        "watchlist_snapshot": [],
                        "resolved_tickers": ["AAPL"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": None,
                    "completed_at": "2026-07-04T11:00:00",
                    "last_error": None,
                    "last_queued_count": 0,
                    "run_ids": [],
                }
            ]
        },
        "watchlist": {"tickers": [{"ticker": "MSFT"}]},
        "unrelated": {"keep": True},
    }
    saved: list[dict[str, object]] = []
    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: saved.append(deepcopy(settings)))
    monkeypatch.setattr(task_module, "list_stock_groups", lambda tenant_id=None: [])

    state["one_time_tasks"]["items"][0]["status"] = "scheduled"

    updated = task_module.update_one_time_task(
        "task-1",
        OneTimeTaskUpdate(
            name="Editable",
            scheduled_for="2026-07-10 22:30",
            analysis_date="2026-07-12",
            manual_stocks=[{"market": "us", "symbol": "NVDA"}],
            group_ids=[],
            include_watchlist=True,
            analysis_config=AutomationAnalysisConfig(
                analysts=["market"],
                llm_provider="openai",
                quick_think_model="gpt-5.4-mini",
                deep_think_model="gpt-5.5",
                research_depth=1,
                output_language="English",
            ),
        ),
        now=datetime.datetime(2026, 7, 4, 11, 0, 0),
    )

    assert updated is not None
    assert saved and len(saved) == 1
    saved_task = saved[0]["one_time_tasks"]["items"][0]
    assert saved[0]["unrelated"] == {"keep": True}
    assert saved_task["name"] == "Editable"
    assert saved_task["scheduled_for"] == "2026-07-10 22:30"
    assert saved_task["analysis_date"] == "2026-07-12"
    assert saved_task["selection_snapshot"]["watchlist_snapshot"] == ["MSFT"]
    assert saved_task["selection_snapshot"]["resolved_tickers"] == ["NVDA", "MSFT"]
    assert saved_task["selection_snapshot"]["include_watchlist"] is True


def test_cancel_one_time_task_persists_cancelled_status(monkeypatch):
    state = {
        "one_time_tasks": {
            "items": [
                {
                    "id": "task-1",
                    "name": "Scheduled A",
                    "status": "scheduled",
                    "scheduled_for": "2026-07-10 21:30",
                    "analysis_date": "2026-07-10",
                    "selection_snapshot": {
                        "manual_stocks": [{"market": "us", "symbol": "AAPL"}],
                        "group_snapshots": [],
                        "include_watchlist": False,
                        "watchlist_snapshot": [],
                        "resolved_tickers": ["AAPL"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": None,
                    "completed_at": None,
                    "last_error": None,
                    "last_queued_count": 0,
                    "run_ids": [],
                }
            ]
        },
        "unrelated": {"keep": True},
    }
    saved: list[dict[str, object]] = []
    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: saved.append(deepcopy(settings)))

    cancelled = task_module.cancel_one_time_task("task-1", now=datetime.datetime(2026, 7, 4, 11, 0, 0))

    assert cancelled is not None
    assert cancelled.status == "cancelled"
    assert saved and len(saved) == 1
    assert saved[0]["unrelated"] == {"keep": True}
    assert saved[0]["one_time_tasks"]["items"][0]["status"] == "cancelled"
    assert saved[0]["one_time_tasks"]["items"][0]["updated_at"] == "2026-07-04T11:00:00"


def test_get_one_time_task_page_filters_and_paginates(monkeypatch):
    state = {
        "one_time_tasks": {
            "items": [
                {
                    "id": "task-1",
                    "name": "Scheduled A",
                    "status": "scheduled",
                    "scheduled_for": "2026-07-10 21:30",
                    "analysis_date": "2026-07-10",
                    "selection_snapshot": {
                        "manual_stocks": [{"market": "us", "symbol": "AAPL"}],
                        "group_snapshots": [],
                        "include_watchlist": False,
                        "watchlist_snapshot": [],
                        "resolved_tickers": ["AAPL"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": None,
                    "completed_at": None,
                    "last_error": None,
                    "last_queued_count": 0,
                    "run_ids": [],
                },
                {
                    "id": "task-2",
                    "name": "Completed B",
                    "status": "completed",
                    "scheduled_for": "2026-07-09 21:30",
                    "analysis_date": "2026-07-09",
                    "selection_snapshot": {
                        "manual_stocks": [{"market": "us", "symbol": "MSFT"}],
                        "group_snapshots": [],
                        "include_watchlist": False,
                        "watchlist_snapshot": [],
                        "resolved_tickers": ["MSFT"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T11:00:00",
                    "updated_at": "2026-07-04T11:00:00",
                    "triggered_at": None,
                    "completed_at": "2026-07-04T12:00:00",
                    "last_error": None,
                    "last_queued_count": 0,
                    "run_ids": [],
                },
            ]
        }
    }
    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: state.update(settings))

    page = task_module.get_one_time_task_page(status="scheduled", page=1, page_size=1)

    assert page.total_count == 1
    assert page.page == 1
    assert page.page_size == 1
    assert [item.id for item in page.items] == ["task-1"]


def test_refresh_one_time_tasks_moves_queued_and_running_tasks_forward(monkeypatch):
    state = {
        "one_time_tasks": {
            "items": [
                {
                    "id": "queued-task",
                    "name": "Queued task",
                    "status": "queued",
                    "scheduled_for": "2026-07-10 21:30",
                    "analysis_date": "2026-07-11",
                    "selection_snapshot": {
                        "manual_stocks": [],
                        "group_snapshots": [],
                        "include_watchlist": False,
                        "watchlist_snapshot": [],
                        "resolved_tickers": ["AAPL"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": "2026-07-10T21:30:00",
                    "completed_at": None,
                    "last_error": None,
                    "last_queued_count": 1,
                    "run_ids": ["run-queued"],
                },
                {
                    "id": "running-task",
                    "name": "Running task",
                    "status": "running",
                    "scheduled_for": "2026-07-10 21:31",
                    "analysis_date": "2026-07-11",
                    "selection_snapshot": {
                        "manual_stocks": [],
                        "group_snapshots": [],
                        "include_watchlist": False,
                        "watchlist_snapshot": [],
                        "resolved_tickers": ["NVDA"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": "2026-07-10T21:31:00",
                    "completed_at": None,
                    "last_error": None,
                    "last_queued_count": 1,
                    "run_ids": ["run-running"],
                },
            ]
        }
    }

    class FakeService:
        def get_run(self, run_id):
            statuses = {
                "run-queued": SimpleNamespace(status="completed"),
                "run-running": SimpleNamespace(status="running"),
            }
            return statuses.get(run_id)

    saved: list[dict[str, object]] = []
    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: saved.append(deepcopy(settings)))
    monkeypatch.setattr(task_module, "get_service", lambda tenant_id=None: FakeService())

    task_module.refresh_one_time_tasks(now=datetime.datetime(2026, 7, 10, 21, 35, 0))

    assert saved
    tasks = saved[-1]["one_time_tasks"]["items"]
    assert tasks[0]["status"] == "completed"
    assert tasks[0]["completed_at"] == "2026-07-10T21:35:00"
    assert tasks[1]["status"] == "running"


def test_process_due_one_time_tasks_marks_missed_and_queues_current_minute(monkeypatch):
    state = {
        "one_time_tasks": {
            "items": [
                {
                    "id": "due-now",
                    "name": "Due now",
                    "status": "scheduled",
                    "scheduled_for": "2026-07-10 21:30",
                    "analysis_date": "2026-07-11",
                    "selection_snapshot": {
                        "manual_stocks": [],
                        "group_snapshots": [],
                        "include_watchlist": False,
                        "watchlist_snapshot": [],
                        "resolved_tickers": ["AAPL"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": None,
                    "completed_at": None,
                    "last_error": None,
                    "last_queued_count": 0,
                    "run_ids": [],
                },
                {
                    "id": "missed",
                    "name": "Missed",
                    "status": "scheduled",
                    "scheduled_for": "2026-07-10 21:29",
                    "analysis_date": "2026-07-11",
                    "selection_snapshot": {
                        "manual_stocks": [],
                        "group_snapshots": [],
                        "include_watchlist": False,
                        "watchlist_snapshot": [],
                        "resolved_tickers": ["NVDA"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": None,
                    "completed_at": None,
                    "last_error": None,
                    "last_queued_count": 0,
                    "run_ids": [],
                },
            ]
        }
    }
    saved: list[dict[str, object]] = []
    created = []

    class FakeService:
        def load_tenant_settings(self):
            return {}

        def create_run(self, req, *, start_worker=True, settings=None):
            created.append((req, start_worker, settings))
            return SimpleNamespace(run_id=f"run-{len(created)}", status="queued", ticker=req.ticker, date=req.date)

    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: saved.append(deepcopy(settings)))
    monkeypatch.setattr(task_module, "get_service", lambda tenant_id=None: FakeService())

    queued = task_module.process_due_one_time_tasks(
        now=datetime.datetime(2026, 7, 10, 21, 30, 5),
        start_worker=False,
    )

    assert queued == 1
    assert created[0][0].ticker == "AAPL"
    assert created[0][0].date == "2026-07-11"
    assert created[0][1] is False
    tasks = saved[-1]["one_time_tasks"]["items"]
    assert tasks[0]["status"] == "queued"
    assert tasks[0]["triggered_at"] == "2026-07-10T21:30:05"
    assert tasks[0]["run_ids"] == ["run-1"]
    assert tasks[1]["status"] == "missed"


def test_process_due_one_time_tasks_infers_crypto_asset_type_for_btc(monkeypatch):
    state = {
        "one_time_tasks": {
            "items": [
                {
                    "id": "btc-task",
                    "name": "BTC task",
                    "status": "scheduled",
                    "scheduled_for": "2026-07-10 21:30",
                    "analysis_date": "2026-07-11",
                    "selection_snapshot": {
                        "manual_stocks": [],
                        "group_snapshots": [],
                        "include_watchlist": False,
                        "watchlist_snapshot": [],
                        "resolved_tickers": ["BTC"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": None,
                    "completed_at": None,
                    "last_error": None,
                    "last_queued_count": 0,
                    "run_ids": [],
                }
            ]
        }
    }
    created = []

    class FakeService:
        def load_tenant_settings(self):
            return {}

        def create_run(self, req, *, start_worker=True, settings=None):
            created.append(req)
            return SimpleNamespace(run_id="run-1", status="queued", ticker=req.ticker, date=req.date)

    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: None)
    monkeypatch.setattr(task_module, "get_service", lambda tenant_id=None: FakeService())

    queued = task_module.process_due_one_time_tasks(
        now=datetime.datetime(2026, 7, 10, 21, 30, 5),
        start_worker=False,
    )

    assert queued == 1
    assert created[0].ticker == "BTC"
    assert created[0].asset_type == "crypto"


def test_process_due_one_time_tasks_keeps_successes_when_a_later_ticker_fails(monkeypatch):
    state = {
        "one_time_tasks": {
            "items": [
                {
                    "id": "partial-failure",
                    "name": "Partial failure",
                    "status": "scheduled",
                    "scheduled_for": "2026-07-10 21:30",
                    "analysis_date": "2026-07-11",
                    "selection_snapshot": {
                        "manual_stocks": [],
                        "group_snapshots": [],
                        "include_watchlist": True,
                        "watchlist_snapshot": ["OLDWL"],
                        "resolved_tickers": ["AAPL", "MSFT"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": None,
                    "completed_at": None,
                    "last_error": None,
                    "last_queued_count": 0,
                    "run_ids": [],
                }
            ]
        },
        "watchlist": {"tickers": [{"ticker": "NEWWATCH"}]},
        "stock_groups": {"items": [{"id": "group-1", "name": "Changed", "tickers": ["NVDA"]}]},
    }
    saved: list[dict[str, object]] = []
    attempted: list[str] = []

    class FakeService:
        def load_tenant_settings(self):
            return {}

        def create_run(self, req, *, start_worker=True, settings=None):
            attempted.append(req.ticker)
            if req.ticker == "MSFT":
                raise RuntimeError("queue failed for MSFT")
            return SimpleNamespace(run_id="run-1", status="queued", ticker=req.ticker, date=req.date)

    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: saved.append(deepcopy(settings)))
    monkeypatch.setattr(task_module, "get_service", lambda tenant_id=None: FakeService())

    queued = task_module.process_due_one_time_tasks(
        now=datetime.datetime(2026, 7, 10, 21, 30, 5),
        start_worker=False,
    )

    assert queued == 1
    assert attempted == ["AAPL", "MSFT"]
    task = saved[-1]["one_time_tasks"]["items"][0]
    assert task["status"] == "queued"
    assert task["run_ids"] == ["run-1"]
    assert task["last_queued_count"] == 1
    assert task["last_error"] == "queue failed for MSFT"
    assert task["triggered_at"] == "2026-07-10T21:30:05"


def test_process_due_one_time_tasks_uses_frozen_resolved_tickers_not_current_sources(monkeypatch):
    state = {
        "one_time_tasks": {
            "items": [
                {
                    "id": "frozen-snapshot",
                    "name": "Frozen snapshot",
                    "status": "scheduled",
                    "scheduled_for": "2026-07-10 21:30",
                    "analysis_date": "2026-07-11",
                    "selection_snapshot": {
                        "manual_stocks": [{"market": "us", "symbol": "AAPL"}],
                        "group_snapshots": [{"id": "group-1", "name": "Old group", "tickers": ["AAPL"]}],
                        "include_watchlist": True,
                        "watchlist_snapshot": ["AAPL"],
                        "resolved_tickers": ["AAPL"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": None,
                    "completed_at": None,
                    "last_error": None,
                    "last_queued_count": 0,
                    "run_ids": [],
                }
            ]
        },
        "watchlist": {"tickers": [{"ticker": "MSFT"}, {"ticker": "NVDA"}]},
        "stock_groups": {"items": [{"id": "group-1", "name": "Changed group", "tickers": ["TSLA", "META"]}]},
    }
    created: list[str] = []
    saved: list[dict[str, object]] = []

    class FakeService:
        def load_tenant_settings(self):
            return {}

        def create_run(self, req, *, start_worker=True, settings=None):
            created.append(req.ticker)
            return SimpleNamespace(run_id=f"run-{len(created)}", status="queued", ticker=req.ticker, date=req.date)

    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: saved.append(deepcopy(settings)))
    monkeypatch.setattr(task_module, "get_service", lambda tenant_id=None: FakeService())

    queued = task_module.process_due_one_time_tasks(
        now=datetime.datetime(2026, 7, 10, 21, 30, 5),
        start_worker=False,
    )

    assert queued == 1
    assert created == ["AAPL"]
    task = saved[-1]["one_time_tasks"]["items"][0]
    assert task["run_ids"] == ["run-1"]
    assert task["last_queued_count"] == 1
    assert task["last_error"] is None


def test_process_due_one_time_tasks_passes_frozen_task_settings_not_live_analysis_settings(monkeypatch):
    state = {
        "one_time_tasks": {
            "items": [
                {
                    "id": "frozen-config",
                    "name": "Frozen config",
                    "status": "scheduled",
                    "scheduled_for": "2026-07-10 21:30",
                    "analysis_date": "2026-07-11",
                    "selection_snapshot": {
                        "manual_stocks": [{"market": "us", "symbol": "AAPL"}],
                        "group_snapshots": [],
                        "include_watchlist": False,
                        "watchlist_snapshot": [],
                        "resolved_tickers": ["AAPL"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "task-quick",
                        "deep_think_model": "task-deep",
                        "research_depth": 3,
                        "output_language": "English",
                        "market_profile": "us",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": None,
                    "completed_at": None,
                    "last_error": None,
                    "last_queued_count": 0,
                    "run_ids": [],
                }
            ]
        }
    }
    captured_settings: list[dict[str, object] | None] = []

    class FakeService:
        def load_tenant_settings(self):
            return {
                "api_keys": {"openai": "live-key"},
                "llm": {
                    "provider": "google",
                    "quick_think_model": "live-quick",
                    "deep_think_model": "live-deep",
                },
                "analysis": {
                    "output_language": "Chinese",
                    "research_depth": 1,
                    "market_profile": "cn_a",
                    "benchmark_ticker": "QQQ",
                },
            }

        def create_run(self, req, *, start_worker=True, settings=None):
            captured_settings.append(deepcopy(settings))
            return SimpleNamespace(run_id="run-1", status="queued", ticker=req.ticker, date=req.date)

    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)
    monkeypatch.setattr(task_module, "save_settings", lambda settings, path=None: None)
    monkeypatch.setattr(task_module, "get_service", lambda tenant_id=None: FakeService())

    queued = task_module.process_due_one_time_tasks(
        now=datetime.datetime(2026, 7, 10, 21, 30, 5),
        start_worker=False,
    )

    assert queued == 1
    assert captured_settings == [
        {
            "api_keys": {"openai": "live-key"},
            "llm": {
                "provider": "openai",
                "quick_think_model": "task-quick",
                "deep_think_model": "task-deep",
            },
            "analysis": {
                "output_language": "English",
                "market_profile": "us",
                "research_depth": 3,
            },
        }
    ]


def test_process_due_one_time_tasks_marks_all_failed_attempts_non_scheduled_and_not_retried(monkeypatch):
    state = {
        "one_time_tasks": {
            "items": [
                {
                    "id": "all-failed",
                    "name": "All failed",
                    "status": "scheduled",
                    "scheduled_for": "2026-07-10 21:30",
                    "analysis_date": "2026-07-11",
                    "selection_snapshot": {
                        "manual_stocks": [],
                        "group_snapshots": [],
                        "include_watchlist": False,
                        "watchlist_snapshot": [],
                        "resolved_tickers": ["AAPL", "MSFT"],
                    },
                    "analysis_config": {
                        "analysts": ["market"],
                        "llm_provider": "openai",
                        "quick_think_model": "gpt-5.4-mini",
                        "deep_think_model": "gpt-5.5",
                        "research_depth": 1,
                        "output_language": "English",
                    },
                    "created_at": "2026-07-04T10:00:00",
                    "updated_at": "2026-07-04T10:00:00",
                    "triggered_at": None,
                    "completed_at": None,
                    "last_error": None,
                    "last_queued_count": 0,
                    "run_ids": [],
                }
            ]
        }
    }
    saved: list[dict[str, object]] = []
    attempted: list[str] = []

    class FakeService:
        def load_tenant_settings(self):
            return {}

        def create_run(self, req, *, start_worker=True, settings=None):
            attempted.append(req.ticker)
            raise RuntimeError(f"queue failed for {req.ticker}")

    monkeypatch.setattr(task_module, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        snapshot = deepcopy(settings)
        saved.append(snapshot)
        state.clear()
        state.update(snapshot)

    monkeypatch.setattr(task_module, "save_settings", _save)
    monkeypatch.setattr(task_module, "get_service", lambda tenant_id=None: FakeService())

    first_queued = task_module.process_due_one_time_tasks(
        now=datetime.datetime(2026, 7, 10, 21, 30, 5),
        start_worker=False,
    )

    second_queued = task_module.process_due_one_time_tasks(
        now=datetime.datetime(2026, 7, 10, 21, 31, 5),
        start_worker=False,
    )

    assert first_queued == 0
    assert second_queued == 0
    assert attempted == ["AAPL", "MSFT"]
    task = saved[-1]["one_time_tasks"]["items"][0]
    assert task["status"] == "completed"
    assert task["run_ids"] == []
    assert task["last_queued_count"] == 0
    assert task["last_error"] == "queue failed for MSFT"
    assert task["triggered_at"] == "2026-07-10T21:30:05"
    assert task["completed_at"] == "2026-07-10T21:30:05"

    with pytest.raises(ValueError, match="Only scheduled tasks can be edited"):
        task_module.update_one_time_task(
            "all-failed",
            OneTimeTaskUpdate(
                name="All failed",
                scheduled_for="2026-07-10 21:32",
                analysis_date="2026-07-11",
                manual_stocks=[{"market": "us", "symbol": "AAPL"}],
                group_ids=[],
                include_watchlist=False,
                analysis_config=AutomationAnalysisConfig(
                    analysts=["market"],
                    llm_provider="openai",
                    quick_think_model="gpt-5.4-mini",
                    deep_think_model="gpt-5.5",
                    research_depth=1,
                    output_language="English",
                ),
            ),
            now=datetime.datetime(2026, 7, 10, 21, 31, 5),
        )

    with pytest.raises(ValueError, match="Only scheduled tasks can be cancelled"):
        task_module.cancel_one_time_task(
            "all-failed",
            now=datetime.datetime(2026, 7, 10, 21, 31, 5),
        )
