"""Route-level tests for the FastAPI web layer."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.service.runtime_context import build_runtime_context
from web.app import app
from web import automation as web_automation
from web import routes as web_routes
from web.runner import RunState


def _make_run(run_id: str = "run-1") -> RunState:
    runtime_context = build_runtime_context(run_id)
    return RunState(
        run_id=run_id,
        ticker="AAPL",
        date="2026-01-15",
        asset_type="stock",
        config=DEFAULT_CONFIG.copy(),
        selected_analysts=["market"],
        runtime_context=runtime_context,
    )


def test_put_settings_exports_to_current_process(monkeypatch):
    captured: dict[str, object] = {}
    client = TestClient(app)

    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: {})
    monkeypatch.setattr(web_routes, "save_settings", lambda settings, path=None: captured.setdefault("saved", settings))

    def _capture_export(settings, overwrite=False):
        captured["exported"] = settings
        captured["overwrite"] = overwrite

    monkeypatch.setattr(web_routes, "export_api_keys_to_env", _capture_export)

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: None)

    response = client.put(
        "/api/settings",
        json={
            "api_keys": {"openai": "sk-test"},
            "analysis": {
                "market_profile": "cn_a",
                "checkpoint_enabled": True,
                "benchmark_ticker": "QQQ",
                "memory_log_max_entries": 25,
            },
            "data": {
                "global_news_queries": ["asia earnings outlook"],
                "tool_vendors": {"get_global_news": "alpha_vantage"},
            },
            "workspace": {
                "default_home_view": "saved-view",
                "default_saved_view_id": "view-a",
            },
        },
    )

    assert response.status_code == 200
    assert captured["overwrite"] is True
    assert captured["saved"]["api_keys"]["openai"] == "sk-test"
    assert captured["exported"]["analysis"]["market_profile"] == "cn_a"
    assert captured["exported"]["analysis"]["benchmark_ticker"] == "QQQ"
    assert captured["exported"]["analysis"]["memory_log_max_entries"] == 25
    assert captured["exported"]["data"]["global_news_queries"] == ["asia earnings outlook"]
    assert captured["exported"]["data"]["tool_vendors"]["get_global_news"] == "alpha_vantage"
    assert captured["saved"]["workspace"]["default_home_view"] == "saved-view"
    assert captured["saved"]["workspace"]["default_saved_view_id"] == "view-a"


def test_settings_are_scoped_by_request_tenant(monkeypatch, tmp_path):
    client = TestClient(app)
    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")

    tenant_a = client.put(
        "/api/settings",
        headers={"X-TradingAgents-Tenant": "tenant-a"},
        json={"analysis": {"output_language": "Chinese"}},
    )
    tenant_b = client.get("/api/settings", headers={"X-TradingAgents-Tenant": "tenant-b"})

    assert tenant_a.status_code == 200
    assert tenant_b.status_code == 200
    assert tenant_b.json()["analysis"]["output_language"] == "English"


def test_settings_security_token_is_masked(monkeypatch, tmp_path):
    client = TestClient(app)
    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant-a.json")

    response = client.put(
        "/api/settings",
        headers={"X-TradingAgents-Tenant": "tenant-a"},
        json={"security": {"web_api_token": "tenant-secret"}},
    )

    assert response.status_code == 200
    assert response.json()["security"]["web_api_token"] == "***"


def test_settings_webhook_token_is_masked(monkeypatch, tmp_path):
    client = TestClient(app)
    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant-a.json")

    response = client.put(
        "/api/settings",
        headers={"X-TradingAgents-Tenant": "tenant-a"},
        json={
            "integrations": {
                "webhook": {
                    "enabled": True,
                    "url": "https://example.com/webhook",
                    "bearer_token": "secret-token",
                    "event_kinds": ["run", "alert"],
                }
            }
        },
    )

    assert response.status_code == 200
    assert response.json()["integrations"]["webhook"]["bearer_token"] == "***"
    assert response.json()["integrations"]["webhook"]["enabled"] is True


def test_list_runs_returns_history(monkeypatch):
    client = TestClient(app)
    old_run = _make_run("old")
    old_run.created_at = "2026-01-15T00:00:00"
    new_run = _make_run("new")
    new_run.created_at = "2026-01-15T01:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [new_run, old_run])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: 2 if run_id == "new" else None)

    response = client.get("/api/runs")

    assert response.status_code == 200
    payload = response.json()
    assert [item["run_id"] for item in payload] == ["new", "old"]
    assert payload[0]["ticker"] == "AAPL"
    assert payload[0]["queue_position"] == 2


def test_list_runs_can_filter_by_query_status_provider_and_asset(monkeypatch):
    client = TestClient(app)

    completed = _make_run("nvda-openai")
    completed.ticker = "NVDA"
    completed.status = "completed"
    completed.signal = "Buy"
    completed.asset_type = "stock"
    completed.created_at = "2026-01-15T01:00:00"
    completed.config["llm_provider"] = "openai"

    failed = _make_run("btc-google")
    failed.ticker = "BTC-USD"
    failed.status = "failed"
    failed.error = "timeout"
    failed.asset_type = "crypto"
    failed.created_at = "2026-01-15T00:00:00"
    failed.config["llm_provider"] = "google"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [completed, failed])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get(
        "/api/runs",
        params={"q": "nvda", "status": "completed", "provider": "openai", "asset_type": "stock"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [item["run_id"] for item in payload] == ["nvda-openai"]
    assert payload[0]["status"] == "completed"
    assert payload[0]["asset_type"] == "stock"


def test_list_runs_can_filter_by_archive_scope(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"archived_runs": {"ids": ["archived-run"]}}

    active = _make_run("active-run")
    active.created_at = "2026-01-15T01:00:00"
    archived = _make_run("archived-run")
    archived.created_at = "2026-01-15T00:00:00"

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [active, archived])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    active_resp = client.get("/api/runs", params={"archived": "active"})
    archived_resp = client.get("/api/runs", params={"archived": "archived"})
    all_resp = client.get("/api/runs", params={"archived": "all"})

    assert [item["run_id"] for item in active_resp.json()] == ["active-run"]
    assert [item["run_id"] for item in archived_resp.json()] == ["archived-run"]
    assert [item["run_id"] for item in all_resp.json()] == ["active-run", "archived-run"]
    assert all_resp.json()[1]["archived"] is True


def test_run_history_export_csv_returns_filtered_rows(monkeypatch):
    client = TestClient(app)

    completed = _make_run("nvda-openai")
    completed.ticker = "NVDA"
    completed.status = "completed"
    completed.signal = "Buy"
    completed.asset_type = "stock"
    completed.created_at = "2026-01-15T01:00:00"
    completed.config["llm_provider"] = "openai"

    failed = _make_run("btc-google")
    failed.ticker = "BTC-USD"
    failed.status = "failed"
    failed.error = "timeout"
    failed.asset_type = "crypto"
    failed.created_at = "2026-01-15T00:00:00"
    failed.config["llm_provider"] = "google"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [completed, failed])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/runs/export", params={"status": "failed"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "tradingagents-run-history-default-" in response.headers["content-disposition"]
    assert "run_id,ticker,date,status,asset_type,llm_provider,created_at,completed_at,queue_position,signal,error" in response.text
    assert "btc-google,BTC-USD,2026-01-15,failed,crypto,google,2026-01-15T00:00:00" in response.text
    assert "nvda-openai" not in response.text


def test_bulk_delete_runs_deletes_terminal_and_skips_active(monkeypatch, tmp_path):
    client = TestClient(app)
    active_run = _make_run("active")
    active_run.status = "running"
    deleted_run = _make_run("done")
    deleted_run.status = "completed"

    deleted_ids: list[str] = []

    def _delete(run_id, tenant_id=None):
        if run_id == "done":
            deleted_ids.append(run_id)
            return deleted_run
        return None

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: {"archived_runs": {"ids": []}})
    monkeypatch.setattr(web_routes, "delete_run", _delete)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: active_run if run_id == "active" else None)

    response = client.post("/api/runs/bulk", json={"ids": ["done", "active", "missing"], "action": "delete"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "delete"
    assert payload["deleted"] == 1
    assert payload["retried"] == 0
    assert payload["skipped"] == 2
    assert deleted_ids == ["done"]


def test_bulk_retry_runs_retries_terminal_and_skips_active(monkeypatch, tmp_path):
    client = TestClient(app)
    active_run = _make_run("active")
    active_run.status = "running"
    retried_run = _make_run("retry-new")
    retried_run.status = "queued"

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: {"archived_runs": {"ids": []}})
    monkeypatch.setattr(web_routes, "retry_run", lambda run_id, tenant_id=None: retried_run if run_id == "done" else None)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: active_run if run_id == "active" else None)

    response = client.post("/api/runs/bulk", json={"ids": ["done", "active"], "action": "retry"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["action"] == "retry"
    assert payload["deleted"] == 0
    assert payload["retried"] == 1
    assert payload["skipped"] == 1


def test_bulk_archive_and_restore_runs_update_archived_ids(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"archived_runs": {"ids": []}}
    terminal = _make_run("done")
    terminal.status = "completed"
    active = _make_run("active")
    active.status = "running"

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: terminal if run_id == "done" else active if run_id == "active" else None)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    archive = client.post("/api/runs/bulk", json={"ids": ["done", "active"], "action": "archive"})

    assert archive.status_code == 200
    assert archive.json()["archived"] == 1
    assert archive.json()["skipped"] == 1
    assert state["archived_runs"]["ids"] == ["done"]

    restore = client.post("/api/runs/bulk", json={"ids": ["done"], "action": "restore"})
    assert state["archived_runs"]["ids"] == []
    assert restore.status_code == 200
    assert restore.json()["restored"] == 1


def test_batch_run_endpoint_queues_manual_tickers(monkeypatch):
    client = TestClient(app)
    created: list[object] = []

    def _create(req, _loop=None, tenant_id=None):
        created.append(req)
        run = _make_run(f"{req.ticker.lower()}-{len(created)}")
        run.ticker = req.ticker
        run.date = req.date
        run.asset_type = req.asset_type
        run.status = "queued"
        return run

    monkeypatch.setattr(web_routes, "create_run", _create)

    response = client.post(
        "/api/runs/batch",
        json={
            "tickers": [" nvda ", "BTC-USD", "nvda"],
            "date": "2026-01-15",
            "analysts": ["market", "news"],
            "llm_provider": "openai",
            "quick_think_model": "gpt-5.4-mini",
            "deep_think_model": "gpt-5.5",
            "research_depth": 3,
            "output_language": "English",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source"] == "manual"
    assert payload["requested_count"] == 2
    assert payload["created_count"] == 2
    assert payload["tickers"] == ["NVDA", "BTC-USD"]
    assert [item["ticker"] for item in payload["runs"]] == ["NVDA", "BTC-USD"]
    assert [item.asset_type for item in created] == ["stock", "crypto"]


def test_batch_run_endpoint_can_queue_watchlist(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {
            "tickers": [
                {"ticker": "NVDA", "created_at": "2026-01-15T01:00:00"},
                {"ticker": "MSFT", "created_at": "2026-01-15T01:05:00"},
                {"ticker": "NVDA", "created_at": "2026-01-15T01:10:00"},
            ]
        }
    }
    created: list[object] = []

    def _create(req, _loop=None, tenant_id=None):
        created.append(req)
        run = _make_run(f"{req.ticker.lower()}-{len(created)}")
        run.ticker = req.ticker
        run.date = req.date
        run.asset_type = req.asset_type
        run.status = "queued"
        return run

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "create_run", _create)

    response = client.post(
        "/api/runs/batch",
        json={
            "source": "watchlist",
            "date": "2026-01-15",
            "analysts": ["market"],
            "llm_provider": "openai",
            "quick_think_model": "gpt-5.4-mini",
            "deep_think_model": "gpt-5.5",
            "research_depth": 1,
            "output_language": "English",
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["source"] == "watchlist"
    assert payload["requested_count"] == 2
    assert payload["created_count"] == 2
    assert payload["tickers"] == ["NVDA", "MSFT"]
    assert [item.ticker for item in created] == ["NVDA", "MSFT"]


def test_batch_run_endpoint_rejects_empty_manual_batch():
    client = TestClient(app)

    response = client.post(
        "/api/runs/batch",
        json={
            "tickers": [],
            "date": "2026-01-15",
            "analysts": ["market"],
            "llm_provider": "openai",
            "quick_think_model": "gpt-5.4-mini",
            "deep_think_model": "gpt-5.5",
            "research_depth": 1,
            "output_language": "English",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Provide at least one ticker or use the watchlist source."


def test_automation_endpoints_round_trip(monkeypatch):
    client = TestClient(app)
    state: dict[str, object] = {}
    created = []

    class FakeService:
        def load_tenant_settings(self):
            return {}

        def create_run(self, req, *, start_worker=True, settings=None):
            created.append(req)
            return type("FakeRun", (), {
                "run_id": f"{req.ticker.lower()}-{len(created)}",
                "status": "queued",
                "ticker": req.ticker,
                "date": req.date,
            })()

    monkeypatch.setattr(web_automation, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_automation, "save_settings", lambda settings, path=None: state.update(settings))
    monkeypatch.setattr(web_automation, "get_service", lambda tenant_id=None: FakeService())

    create = client.post(
        "/api/automations",
        json={
            "name": "Friday Basket",
            "enabled": True,
            "source": "manual",
            "tickers": ["NVDA", "BTC-USD"],
            "cadence": "weekly",
            "weekday": "fri",
            "time_of_day": "09:30",
            "analysis_config": {
                "analysts": ["market"],
                "llm_provider": "openai",
                "quick_think_model": "gpt-5.4-mini",
                "deep_think_model": "gpt-5.5",
                "research_depth": 1,
                "output_language": "English",
            },
        },
    )
    rule_id = create.json()["id"]
    listed = client.get("/api/automations")
    toggled = client.patch(f"/api/automations/{rule_id}", json={"enabled": False})
    ran = client.post(f"/api/automations/{rule_id}/run-now")
    deleted = client.delete(f"/api/automations/{rule_id}")

    assert create.status_code == 201
    assert listed.status_code == 200
    assert toggled.status_code == 200
    assert ran.status_code == 200
    assert deleted.status_code == 200
    assert listed.json()[0]["name"] == "Friday Basket"
    assert toggled.json()["enabled"] is False
    assert ran.json()["created_count"] == 2
    assert ran.json()["tickers"] == ["NVDA", "BTC-USD"]
    assert deleted.json()["deleted"] == 1


def test_system_status_triggers_local_due_automations(monkeypatch):
    client = TestClient(app)
    calls = []

    monkeypatch.setattr(web_routes, "_process_due_automations_if_local", lambda tenant_id=None: calls.append(tenant_id))
    monkeypatch.setattr(web_routes, "get_service_status", lambda tenant_id=None: {
        "queue_depth": 0,
        "run_count": 0,
        "worker_running": False,
        "worker_mode": "local_thread",
        "worker_last_seen": None,
    })
    monkeypatch.setattr(web_routes, "get_state_location", lambda tenant_id=None: "/tmp/state")
    monkeypatch.setattr(web_routes, "get_auth_scope", lambda tenant_id=None: "disabled")

    response = client.get("/api/system/status", headers={"X-TradingAgents-Tenant": "desk-a"})

    assert response.status_code == 200
    assert calls == ["desk-a"]


def test_system_status_triggers_local_webhook_delivery(monkeypatch):
    client = TestClient(app)
    calls = []

    monkeypatch.setattr(web_routes, "_process_due_automations_if_local", lambda tenant_id=None: None)
    monkeypatch.setattr(web_routes, "_process_webhook_notifications_if_local", lambda tenant_id=None: calls.append(tenant_id))
    monkeypatch.setattr(web_routes, "get_service_status", lambda tenant_id=None: {
        "queue_depth": 0,
        "run_count": 0,
        "worker_running": False,
        "worker_mode": "local_thread",
        "worker_last_seen": None,
    })
    monkeypatch.setattr(web_routes, "get_state_location", lambda tenant_id=None: "/tmp/state")
    monkeypatch.setattr(web_routes, "get_auth_scope", lambda tenant_id=None: "disabled")

    response = client.get("/api/system/status", headers={"X-TradingAgents-Tenant": "desk-a"})

    assert response.status_code == 200
    assert calls == ["desk-a"]


def test_get_ticker_overview_aggregates_recent_runs(monkeypatch):
    client = TestClient(app)
    newest = _make_run("new")
    newest.ticker = "NVDA"
    newest.status = "completed"
    newest.signal = "Buy"
    newest.created_at = "2026-01-15T01:00:00"

    older = _make_run("old")
    older.ticker = "NVDA"
    older.status = "failed"
    older.error = "provider timeout"
    older.created_at = "2026-01-15T00:00:00"

    other = _make_run("other")
    other.ticker = "AAPL"
    other.created_at = "2026-01-16T00:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [other, newest, older])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/tickers/NVDA")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "NVDA"
    assert payload["run_count"] == 2
    assert payload["latest_run_id"] == "new"
    assert payload["latest_signal"] == "Buy"
    assert payload["latest_status"] == "completed"
    assert [item["run_id"] for item in payload["recent_runs"]] == ["new", "old"]


def test_get_ticker_overview_returns_empty_summary_when_no_runs(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    response = client.get("/api/tickers/MSFT")

    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "MSFT"
    assert payload["run_count"] == 0
    assert payload["recent_runs"] == []
    assert payload["latest_run_id"] is None


def test_watchlist_endpoint_returns_tenant_scoped_entries(monkeypatch, tmp_path):
    client = TestClient(app)
    saved = {"watchlist": {"tickers": ["NVDA", "MSFT"]}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: saved)

    newest = _make_run("new")
    newest.ticker = "NVDA"
    newest.status = "completed"
    newest.signal = "Buy"
    newest.created_at = "2026-01-15T01:00:00"

    older = _make_run("old")
    older.ticker = "NVDA"
    older.status = "failed"
    older.error = "provider timeout"
    older.created_at = "2026-01-15T00:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [newest, older])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/watchlist")

    assert response.status_code == 200
    payload = response.json()
    assert [item["ticker"] for item in payload] == ["NVDA", "MSFT"]
    assert payload[0]["run_count"] == 2
    assert payload[0]["latest_signal"] == "Buy"
    assert payload[1]["run_count"] == 0


def test_watchlist_post_adds_normalized_ticker_once(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"watchlist": {"tickers": ["AAPL"]}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post("/api/watchlist", json={"ticker": " nvda "})
    response_dup = client.post("/api/watchlist", json={"ticker": "NVDA"})

    assert response.status_code == 201
    assert response.json()["ticker"] == "NVDA"
    assert response_dup.status_code == 201
    assert state["watchlist"]["tickers"] == ["AAPL", "NVDA"]


def test_watchlist_delete_removes_saved_ticker(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"watchlist": {"tickers": ["AAPL", "NVDA"]}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.delete("/api/watchlist/NVDA")

    assert response.status_code == 200
    assert response.json() == {"deleted": 1}
    assert state["watchlist"]["tickers"] == ["AAPL"]


def test_watchlist_import_persists_unique_tickers_and_reports_duplicates(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"watchlist": {"tickers": ["AAPL"]}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post(
        "/api/watchlist/import",
        json={"content": "ticker,name\nnvda,NVIDIA\nAAPL,Apple\nmsft,Microsoft\nnvda,NVIDIA"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported_count"] == 2
    assert payload["skipped_count"] == 2
    assert payload["error_count"] == 0
    assert payload["errors"] == []
    assert [item["ticker"] for item in state["watchlist"]["tickers"]] == ["AAPL", "NVDA", "MSFT"]


def test_watchlist_import_rejects_blank_content(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"watchlist": {"tickers": []}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    response = client.post("/api/watchlist/import", json={"content": "   \n\t"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Import content must not be blank."


def test_compare_runs_returns_side_by_side_payload(monkeypatch):
    client = TestClient(app)

    left = _make_run("left")
    left.ticker = "NVDA"
    left.status = "completed"
    left.signal = "Buy"
    left.created_at = "2026-01-15T01:00:00"
    left.report_sections["final_trade_decision"] = "Rating: Buy"
    left.config.update({"llm_provider": "openai", "max_debate_rounds": 3})

    right = _make_run("right")
    right.ticker = "NVDA"
    right.status = "completed"
    right.signal = "Hold"
    right.created_at = "2026-01-16T01:00:00"
    right.report_sections["final_trade_decision"] = "Rating: Hold"
    right.config.update({"llm_provider": "google", "max_debate_rounds": 5})

    monkeypatch.setattr(
        web_routes,
        "get_run",
        lambda run_id, tenant_id=None: {"left": left, "right": right}.get(run_id),
    )
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/runs/compare", params={"left_run_id": "left", "right_run_id": "right"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["left"]["run_id"] == "left"
    assert payload["right"]["run_id"] == "right"
    assert payload["left"]["signal"] == "Buy"
    assert payload["right"]["signal"] == "Hold"
    assert "llm_provider" in payload["differing_summary_fields"]
    assert "final_trade_decision" in payload["differing_sections"]


def test_compare_runs_404s_when_run_missing(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: None)

    response = client.get("/api/runs/compare", params={"left_run_id": "left", "right_run_id": "right"})

    assert response.status_code == 404


def test_run_chat_answers_question_from_saved_run_context(monkeypatch, tmp_path):
    client = TestClient(app)
    run = _make_run("chat-run")
    run.final_report = "# Trading Analysis Report\n\nBull case is stronger than bear case."
    run.config.update({
        "llm_provider": "openai",
        "deep_think_llm": "gpt-5.5",
        "backend_url": "https://example.invalid/v1",
        "temperature": 0.2,
        "openai_reasoning_effort": "medium",
    })

    class FakeLLM:
        def __init__(self):
            self.seen_prompt = None

        def invoke(self, prompt):
            self.seen_prompt = prompt
            return type("Resp", (), {"content": "Because the saved report says the bull case is stronger."})()

    fake_llm = FakeLLM()

    class FakeClient:
        def get_llm(self):
            return fake_llm

    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run)
    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: {"api_keys": {"openai": "sk-test"}})
    monkeypatch.setattr(web_routes, "export_api_keys_to_env", lambda settings=None, overwrite=False, path=None: None)
    monkeypatch.setattr("web.routes.create_llm_client", lambda provider, model, base_url=None, **kwargs: FakeClient())

    response = client.post(
        f"/api/runs/{run.run_id}/chat",
        json={
            "question": "Why is this a buy?",
            "history": [{"role": "user", "content": "Summarize the decision."}],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "chat-run"
    assert payload["provider"] == "openai"
    assert payload["model"] == "gpt-5.5"
    assert "bull case is stronger" in payload["answer"]
    assert "Summarize the decision." in fake_llm.seen_prompt
    assert "Why is this a buy?" in fake_llm.seen_prompt


def test_run_chat_404s_when_run_missing(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: None)

    response = client.post(f"/api/runs/missing/chat", json={"question": "Hello"})

    assert response.status_code == 404


def test_alert_center_returns_rules_and_active_hits(monkeypatch, tmp_path):
    client = TestClient(app)
    settings = {
        "alerts": {
            "rules": [
                {"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy"},
                {"id": "rule-fail", "ticker": "AAPL", "field": "status", "value": "failed"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: settings)

    nvda = _make_run("nvda")
    nvda.ticker = "NVDA"
    nvda.signal = "Buy"
    nvda.status = "completed"
    nvda.date = "2026-01-15"
    nvda.created_at = "2026-01-15T01:00:00"

    aapl = _make_run("aapl")
    aapl.ticker = "AAPL"
    aapl.status = "running"
    aapl.date = "2026-01-16"
    aapl.created_at = "2026-01-16T01:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [nvda, aapl])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/alerts")

    assert response.status_code == 200
    payload = response.json()
    assert [rule["id"] for rule in payload["rules"]] == ["rule-buy", "rule-fail"]
    assert len(payload["hits"]) == 1
    assert payload["hits"][0]["rule_id"] == "rule-buy"
    assert payload["hits"][0]["actual_value"] == "Buy"


def test_alert_rule_post_persists_normalized_rule(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"alerts": {"rules": []}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post(
        "/api/alerts/rules",
        json={"ticker": " nvda ", "field": "signal", "value": " buy "},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["ticker"] == "NVDA"
    assert payload["field"] == "signal"
    assert payload["value"] == "Buy"
    assert len(state["alerts"]["rules"]) == 1


def test_alert_rule_delete_removes_saved_rule(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "alerts": {
            "rules": [
                {"id": "rule-a", "ticker": "AAPL", "field": "signal", "value": "Hold"},
                {"id": "rule-b", "ticker": "NVDA", "field": "signal", "value": "Buy"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.delete("/api/alerts/rules/rule-b")

    assert response.status_code == 200
    assert response.json() == {"deleted": 1}
    assert [rule["id"] for rule in state["alerts"]["rules"]] == ["rule-a"]


def test_portfolio_endpoint_returns_positions_with_summary(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "portfolio": {
            "positions": [
                {"id": "pos-a", "ticker": "NVDA", "quantity": 10, "average_cost": 100.0},
                {"id": "pos-b", "ticker": "AAPL", "quantity": 5, "average_cost": 200.0},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    nvda = _make_run("nvda")
    nvda.ticker = "NVDA"
    nvda.signal = "Buy"
    nvda.status = "completed"
    nvda.date = "2026-01-15"
    nvda.created_at = "2026-01-15T01:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [nvda])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/portfolio")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["position_count"] == 2
    assert payload["summary"]["unique_ticker_count"] == 2
    assert payload["summary"]["total_cost_basis"] == 2000.0
    assert payload["positions"][0]["cost_basis"] == 1000.0
    assert payload["positions"][0]["latest_signal"] == "Buy"
    assert payload["positions"][1]["latest_signal"] is None


def test_portfolio_post_adds_position_and_normalizes_ticker(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"portfolio": {"positions": []}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post(
        "/api/portfolio/positions",
        json={"ticker": " nvda ", "quantity": 3, "average_cost": 125.5},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["ticker"] == "NVDA"
    assert payload["cost_basis"] == 376.5
    assert len(state["portfolio"]["positions"]) == 1


def test_portfolio_delete_removes_position(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "portfolio": {
            "positions": [
                {"id": "pos-a", "ticker": "AAPL", "quantity": 1, "average_cost": 100.0},
                {"id": "pos-b", "ticker": "NVDA", "quantity": 2, "average_cost": 120.0},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.delete("/api/portfolio/positions/pos-b")

    assert response.status_code == 200
    assert response.json() == {"deleted": 1}
    assert [pos["id"] for pos in state["portfolio"]["positions"]] == ["pos-a"]


def test_portfolio_import_adds_positions_and_reports_invalid_rows(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"portfolio": {"positions": []}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post(
        "/api/portfolio/import",
        json={"content": "symbol\tshares\tavg cost\nnvda\t3\t125.5\nmsft\t2\t450\naapl\t0\t210"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["imported_count"] == 2
    assert payload["skipped_count"] == 0
    assert payload["error_count"] == 1
    assert payload["errors"][0]["line_number"] == 4
    assert "quantity" in payload["errors"][0]["message"].lower()
    assert [position["ticker"] for position in state["portfolio"]["positions"]] == ["NVDA", "MSFT"]


def test_portfolio_import_rejects_blank_content(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"portfolio": {"positions": []}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    response = client.post("/api/portfolio/import", json={"content": "\n  "})

    assert response.status_code == 400
    assert response.json()["detail"] == "Import content must not be blank."


def test_daily_briefing_returns_aggregated_workspace_summary(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": ["NVDA", "MSFT"]},
        "alerts": {"rules": [{"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy"}]},
        "portfolio": {"positions": [{"id": "pos-a", "ticker": "NVDA", "quantity": 10, "average_cost": 100.0}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    newest = _make_run("new")
    newest.ticker = "NVDA"
    newest.status = "completed"
    newest.signal = "Buy"
    newest.date = "2026-01-15"
    newest.created_at = "2026-01-15T01:00:00"

    older = _make_run("old")
    older.ticker = "MSFT"
    older.status = "failed"
    older.error = "provider timeout"
    older.date = "2026-01-14"
    older.created_at = "2026-01-14T01:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [newest, older])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/briefing/daily")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["alert_hit_count"] == 1
    assert payload["summary"]["watchlist_count"] == 2
    assert payload["summary"]["portfolio_position_count"] == 1
    assert payload["summary"]["recent_run_count"] == 2
    assert payload["alert_hits"][0]["ticker"] == "NVDA"
    assert payload["watchlist_focus"][0]["ticker"] == "NVDA"
    assert payload["portfolio_focus"][0]["ticker"] == "NVDA"
    assert payload["recent_runs"][0]["run_id"] == "new"


def test_workspace_dashboard_returns_focus_buckets(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": ["NVDA", "AAPL", "MSFT"]},
        "alerts": {"rules": [{"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy"}]},
        "portfolio": {"positions": [{"id": "pos-a", "ticker": "NVDA", "quantity": 10, "average_cost": 100.0}]},
        "dashboard": {"visible_sections": ["bullish_focus", "active_alerts", "pinned_actions", "pending_reviews", "automations", "saved_shortcuts"]},
        "pinned_runs": {"items": [{"run_id": "nvda", "note": "Core thesis", "category": "high-conviction", "priority": "p1", "next_action": "Review after earnings", "action_status": "todo", "due_date": "2026-01-20", "snoozed_until": None, "created_at": "2026-01-15T02:00:00"}]},
        "run_reviews": {"items": [{"run_id": "nvda", "reviewer": "Alice", "status": "pending", "note": "Check valuation framing.", "created_at": "2026-01-15T02:10:00", "updated_at": "2026-01-15T02:15:00"}]},
        "saved_searches": {"items": [{"id": "search-a", "name": "Pinned Search", "query": "nvda", "kinds": ["run"], "pinned": True, "created_at": "2026-01-15T02:20:00"}]},
        "saved_views": {"items": [{"id": "view-a", "name": "Pinned View", "url": "/?view=briefing", "visible_panels": ["dashboard-panel"], "pinned": True, "created_at": "2026-01-15T02:25:00"}]},
        "automations": {"items": [{"id": "auto-a", "name": "Morning Sweep", "enabled": True, "source": "watchlist", "tickers": [], "cadence": "daily", "time_of_day": "09:00", "created_at": "2026-01-15T02:30:00", "updated_at": "2026-01-15T02:30:00", "analysis_config": {"analysts": ["market"], "llm_provider": "openai", "quick_think_model": "gpt-5.4-mini", "deep_think_model": "gpt-5.5", "research_depth": 1, "output_language": "English"}}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    nvda = _make_run("nvda")
    nvda.ticker = "NVDA"
    nvda.signal = "Buy"
    nvda.status = "completed"
    nvda.date = "2026-01-15"
    nvda.created_at = "2026-01-15T01:00:00"

    aapl = _make_run("aapl")
    aapl.ticker = "AAPL"
    aapl.status = "failed"
    aapl.error = "provider timeout"
    aapl.date = "2026-01-14"
    aapl.created_at = "2026-01-14T01:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [nvda, aapl])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["watchlist_count"] == 3
    assert payload["summary"]["bullish_focus_count"] == 1
    assert payload["summary"]["needs_attention_count"] == 1
    assert payload["summary"]["alert_hit_count"] == 1
    assert payload["summary"]["pinned_action_count"] == 1
    assert payload["summary"]["pending_review_count"] == 1
    assert payload["summary"]["automation_count"] == 1
    assert payload["summary"]["saved_shortcut_count"] == 2
    assert payload["visible_sections"] == ["bullish_focus", "active_alerts", "pinned_actions", "pending_reviews", "automations", "saved_shortcuts"]
    assert payload["section_order"] == ["bullish_focus", "active_alerts", "pinned_actions", "pending_reviews", "automations", "saved_shortcuts", "needs_attention", "portfolio_focus", "operational_runs"]
    assert payload["bullish_focus"][0]["ticker"] == "NVDA"
    assert payload["needs_attention"][0]["ticker"] == "AAPL"
    assert payload["active_alerts"][0]["ticker"] == "NVDA"
    assert payload["portfolio_focus"][0]["ticker"] == "NVDA"
    assert payload["pinned_actions"][0]["run_id"] == "nvda"
    assert payload["pending_reviews"][0]["reviewer"] == "Alice"
    assert payload["automations"][0]["name"] == "Morning Sweep"
    assert len(payload["saved_shortcuts"]) == 2
    assert payload["operational_runs"][0]["run_id"] == "aapl"
    assert payload["getting_started"]["completed_count"] == 5
    assert payload["getting_started"]["remaining_count"] == 1
    assert any(item["id"] == "add_member" and item["completed"] is False for item in payload["getting_started"]["items"])


def test_workspace_dashboard_includes_getting_started_checklist_for_empty_workspace(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["watchlist_count"] == 0
    assert payload["summary"]["recent_run_count"] == 0
    assert payload["getting_started"]["completed_count"] == 0
    assert payload["getting_started"]["remaining_count"] == payload["getting_started"]["total_count"] == 6
    assert [item["id"] for item in payload["getting_started"]["items"]] == [
        "run_analysis",
        "build_watchlist",
        "track_portfolio",
        "save_shortcut",
        "create_automation",
        "add_member",
    ]
    assert all(item["completed"] is False for item in payload["getting_started"]["items"])


def test_workspace_analytics_returns_operational_breakdowns(monkeypatch):
    client = TestClient(app)

    completed = _make_run("done-openai")
    completed.ticker = "NVDA"
    completed.status = "completed"
    completed.signal = "Buy"
    completed.created_at = "2026-01-15T10:00:00"
    completed.started_at = "2026-01-15T10:00:05"
    completed.completed_at = "2026-01-15T10:01:05"
    completed.config["llm_provider"] = "openai"

    failed = _make_run("fail-google")
    failed.ticker = "AAPL"
    failed.status = "failed"
    failed.error = "timeout"
    failed.created_at = "2026-01-15T09:00:00"
    failed.started_at = "2026-01-15T09:00:05"
    failed.completed_at = "2026-01-15T09:00:35"
    failed.config["llm_provider"] = "google"

    queued = _make_run("queued-openai")
    queued.ticker = "NVDA"
    queued.status = "queued"
    queued.signal = None
    queued.created_at = "2026-01-14T08:00:00"
    queued.config["llm_provider"] = "openai"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [completed, failed, queued])

    response = client.get("/api/analytics")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_runs"] == 3
    assert payload["summary"]["terminal_runs"] == 2
    assert payload["summary"]["queued_runs"] == 1
    assert payload["summary"]["success_rate"] == 0.5
    assert payload["summary"]["avg_duration_seconds"] == 45.0
    assert payload["summary"]["unique_ticker_count"] == 2
    assert payload["provider_breakdown"][0]["label"] == "openai"
    assert payload["provider_breakdown"][0]["value"] == 2
    assert payload["asset_type_breakdown"][0]["label"] == "stock"
    assert payload["top_tickers"][0]["label"] == "NVDA"
    assert payload["top_tickers"][0]["value"] == 2
    assert payload["daily_activity"][0]["date"] == "2026-01-15"
    assert payload["daily_activity"][0]["completed_runs"] == 1
    assert payload["daily_activity"][0]["failed_runs"] == 1


def test_workspace_analytics_export_csv_returns_summary_rows(monkeypatch):
    client = TestClient(app)

    completed = _make_run("done-openai")
    completed.ticker = "NVDA"
    completed.status = "completed"
    completed.signal = "Buy"
    completed.asset_type = "stock"
    completed.created_at = "2026-01-15T10:00:00"
    completed.started_at = "2026-01-15T10:00:05"
    completed.completed_at = "2026-01-15T10:01:05"
    completed.config["llm_provider"] = "openai"

    failed = _make_run("fail-google")
    failed.ticker = "AAPL"
    failed.status = "failed"
    failed.error = "timeout"
    failed.asset_type = "stock"
    failed.created_at = "2026-01-15T09:00:00"
    failed.started_at = "2026-01-15T09:00:05"
    failed.completed_at = "2026-01-15T09:01:35"
    failed.config["llm_provider"] = "google"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [completed, failed])

    response = client.get("/api/analytics/export")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "tradingagents-workspace-analytics-default-" in response.headers["content-disposition"]
    assert "section,label,value" in response.text
    assert "summary,total_runs,2" in response.text
    assert "status,completed,1" in response.text
    assert "provider,openai,1" in response.text
    assert "daily_activity,2026-01-15,2" in response.text


def test_workspace_screener_filters_saved_candidates(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"ticker": "NVDA"}, {"ticker": "TSLA"}]},
        "alerts": {"rules": [{"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy"}]},
        "portfolio": {"positions": [{"id": "pos-a", "ticker": "NVDA", "quantity": 10, "average_cost": 100.0}]},
        "pinned_runs": {"items": [{"run_id": "nvda-run", "category": "high-conviction", "priority": "p1", "created_at": "2026-01-15T02:00:00"}]},
        "run_annotations": {"items": [{"run_id": "nvda-run", "label": "Core thesis", "created_at": "2026-01-15T02:00:00", "updated_at": "2026-01-15T02:05:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    nvda = _make_run("nvda-run")
    nvda.ticker = "NVDA"
    nvda.status = "completed"
    nvda.signal = "Buy"
    nvda.created_at = "2026-01-15T03:00:00"
    nvda.config["llm_provider"] = "openai"
    nvda.config["max_debate_rounds"] = 3

    aapl = _make_run("aapl-run")
    aapl.ticker = "AAPL"
    aapl.status = "failed"
    aapl.error = "timeout"
    aapl.signal = "Sell"
    aapl.created_at = "2026-01-15T01:00:00"
    aapl.config["llm_provider"] = "google"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [nvda, aapl])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: nvda if run_id == "nvda-run" else aapl if run_id == "aapl-run" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/screener", params={"signal": "bullish", "provider": "openai"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_candidates"] == 1
    assert payload["summary"]["bullish_count"] == 1
    assert payload["summary"]["alert_hit_count"] == 1
    assert payload["summary"]["watchlist_count"] == 1
    assert payload["summary"]["portfolio_count"] == 1
    assert payload["summary"]["pinned_count"] == 1
    assert payload["rows"][0]["ticker"] == "NVDA"
    assert payload["rows"][0]["has_alert_hit"] is True
    assert payload["rows"][0]["on_watchlist"] is True
    assert payload["rows"][0]["in_portfolio"] is True
    assert payload["rows"][0]["is_pinned"] is True
    assert payload["rows"][0]["annotation_label"] == "Core thesis"


def test_workspace_screener_watchlist_scope_includes_unrun_tickers(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"watchlist": {"tickers": [{"ticker": "TSLA"}]}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    response = client.get("/api/screener", params={"scope": "watchlist"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["total_candidates"] == 1
    assert payload["rows"][0]["ticker"] == "TSLA"
    assert payload["rows"][0]["latest_run_id"] is None
    assert payload["rows"][0]["on_watchlist"] is True


def test_workspace_screener_export_csv_returns_filtered_rows(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"ticker": "NVDA"}]},
        "portfolio": {"positions": [{"id": "pos-a", "ticker": "NVDA", "quantity": 10, "average_cost": 100.0}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    nvda = _make_run("nvda-run")
    nvda.ticker = "NVDA"
    nvda.status = "completed"
    nvda.signal = "Buy"
    nvda.created_at = "2026-01-15T03:00:00"
    nvda.config["llm_provider"] = "openai"

    aapl = _make_run("aapl-run")
    aapl.ticker = "AAPL"
    aapl.status = "failed"
    aapl.signal = "Sell"
    aapl.created_at = "2026-01-15T01:00:00"
    aapl.config["llm_provider"] = "google"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [nvda, aapl])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: nvda if run_id == "nvda-run" else aapl if run_id == "aapl-run" else None)

    response = client.get("/api/screener/export", params={"signal": "bullish", "provider": "openai"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "tradingagents-workspace-screener-default-" in response.headers["content-disposition"]
    assert "ticker,run_count,latest_run_id,latest_signal" in response.text
    assert "NVDA,1,nvda-run,Buy,completed" in response.text
    assert "AAPL" not in response.text


def test_workspace_members_round_trip_and_assignee_updates(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "workspace_members": {"items": []},
        "pinned_runs": {"items": [{"run_id": "run-a", "action_status": "todo", "created_at": "2026-01-10T09:00:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: _make_run("run-a"))

    created = client.post("/api/members", json={"name": "Alice", "role": "reviewer"})
    listed = client.get("/api/members")
    assigned = client.patch("/api/pinned-runs/run-a/assignee", json={"assignee": "Alice"})
    deleted = client.delete(f"/api/members/{created.json()['id']}")

    assert created.status_code == 201
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "Alice"
    assert listed.json()[0]["role"] == "reviewer"
    assert assigned.status_code == 200
    assert assigned.json()["assignee"] == "Alice"
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == 1
    assert state["pinned_runs"]["items"][0].get("assignee") is None


def test_member_workspace_aggregates_actions_mentions_and_comments(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-10T08:00:00"}]},
        "pinned_runs": {"items": [{"run_id": "run-a", "action_status": "todo", "assignee": "Alice", "due_date": "2000-01-01", "created_at": "2026-01-10T09:00:00"}]},
        "run_reviews": {"items": [{"run_id": "run-a", "reviewer": "Alice", "status": "pending", "note": "Check valuation framing.", "created_at": "2026-01-15T01:00:00", "updated_at": "2026-01-15T01:10:00"}]},
        "run_comments": {
            "items": [
                {"id": "comment-a", "run_id": "run-a", "author": "Bob", "content": "Looping in @Alice on the catalyst risk.", "created_at": "2026-01-15T03:00:00"},
                {"id": "comment-b", "run_id": "run-a", "author": "Alice", "content": "I will review this after the close.", "created_at": "2026-01-15T04:00:00"},
            ]
        },
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run = _make_run("run-a")
    run.ticker = "NVDA"
    run.signal = "Buy"
    run.status = "completed"
    run.created_at = "2026-01-15T02:00:00"
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run if run_id == "run-a" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/members/member-a/workspace")

    assert response.status_code == 200
    payload = response.json()
    assert payload["member"]["name"] == "Alice"
    assert payload["summary"]["assigned_action_count"] == 1
    assert payload["summary"]["overdue_action_count"] == 1
    assert payload["summary"]["pending_review_count"] == 1
    assert payload["summary"]["mention_count"] == 1
    assert payload["summary"]["unread_mention_count"] == 1
    assert payload["summary"]["recent_comment_count"] == 1
    assert payload["assigned_actions"][0]["assignee"] == "Alice"
    assert payload["pending_reviews"][0]["reviewer"] == "Alice"
    assert payload["mention_notifications"][0]["kind"] == "comment"
    assert payload["recent_comments"][0]["author"] == "Alice"


def test_notification_center_aggregates_runs_alerts_and_due_actions(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "alerts": {"rules": [{"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy", "created_at": "2026-01-15T00:30:00"}]},
        "pinned_runs": {"items": [{"run_id": "nvda", "note": "Review the thesis", "next_action": "Call out the catalyst", "action_status": "todo", "due_date": "2000-01-01", "created_at": "2026-01-15T00:40:00"}]},
        "notifications": {"read_items": [{"id": "alert:rule-buy:nvda", "read_at": "2026-01-15T03:00:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "save_settings", lambda settings, path=None: state.update(settings))

    nvda = _make_run("nvda")
    nvda.ticker = "NVDA"
    nvda.signal = "Buy"
    nvda.status = "completed"
    nvda.created_at = "2026-01-15T02:00:00"

    fail = _make_run("fail-aapl")
    fail.ticker = "AAPL"
    fail.status = "failed"
    fail.error = "provider timeout"
    fail.created_at = "2026-01-15T01:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [nvda, fail])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: nvda if run_id == "nvda" else fail if run_id == "fail-aapl" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/notifications")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_count"] == 4
    assert payload["unread_count"] == 3
    assert {item["kind"] for item in payload["items"]} == {"run", "alert", "action"}
    assert any(item["id"] == "alert:rule-buy:nvda" and item["is_read"] is True for item in payload["items"])
    assert any(item["id"] == "pin-due:nvda:2000-01-01" and item["severity"] == "error" for item in payload["items"])


def test_notification_center_includes_comment_mentions_and_member_filter(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-10T08:00:00"}]},
        "run_comments": {"items": [{"id": "comment-a", "run_id": "nvda", "author": "Bob", "content": "Looping in @Alice on the catalyst risk.", "created_at": "2026-01-15T03:00:00"}]},
        "pinned_runs": {"items": [{"run_id": "nvda", "action_status": "todo", "assignee": "Alice", "due_date": "2000-01-01", "created_at": "2026-01-10T09:00:00"}]},
        "run_reviews": {"items": [{"run_id": "nvda", "reviewer": "Alice", "status": "pending", "note": "Check the risk framing.", "created_at": "2026-01-15T01:00:00", "updated_at": "2026-01-15T02:30:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run = _make_run("nvda")
    run.ticker = "NVDA"
    run.signal = "Buy"
    run.status = "completed"
    run.created_at = "2026-01-15T02:00:00"
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run if run_id == "nvda" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    all_resp = client.get("/api/notifications")
    member_resp = client.get("/api/notifications", params={"member": "Alice"})

    assert all_resp.status_code == 200
    assert member_resp.status_code == 200
    all_payload = all_resp.json()
    member_payload = member_resp.json()
    assert any(item["kind"] == "comment" and item["member"] == "Alice" for item in all_payload["items"])
    assert any(item["kind"] == "action" and item["member"] == "Alice" for item in all_payload["items"])
    assert any(item["kind"] == "review" and item["member"] == "Alice" for item in all_payload["items"])
    assert member_payload["member_filter"] == "Alice"
    assert {item["kind"] for item in member_payload["items"]} == {"comment", "action", "review"}


def test_notification_center_can_filter_by_kind_and_severity(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "alerts": {"rules": [{"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy", "created_at": "2026-01-15T00:30:00"}]},
        "pinned_runs": {"items": [{"run_id": "nvda", "note": "Review the thesis", "next_action": "Call out the catalyst", "action_status": "todo", "due_date": "2000-01-01", "created_at": "2026-01-15T00:40:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    nvda = _make_run("nvda")
    nvda.ticker = "NVDA"
    nvda.signal = "Buy"
    nvda.status = "completed"
    nvda.created_at = "2026-01-15T02:00:00"

    fail = _make_run("fail-aapl")
    fail.ticker = "AAPL"
    fail.status = "failed"
    fail.error = "provider timeout"
    fail.created_at = "2026-01-15T01:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [nvda, fail])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: nvda if run_id == "nvda" else fail if run_id == "fail-aapl" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    kind_resp = client.get("/api/notifications", params={"kind": "alert"})
    severity_resp = client.get("/api/notifications", params={"severity": "error"})

    assert kind_resp.status_code == 200
    assert severity_resp.status_code == 200
    assert {item["kind"] for item in kind_resp.json()["items"]} == {"alert"}
    assert {item["severity"] for item in severity_resp.json()["items"]} == {"error"}


def test_notification_center_can_mark_one_item_read(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"notifications": {"read_items": []}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "save_settings", lambda settings, path=None: state.update(settings))

    run = _make_run("nvda")
    run.ticker = "NVDA"
    run.signal = "Buy"
    run.status = "completed"
    run.created_at = "2026-01-15T02:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run if run_id == "nvda" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    mark = client.post("/api/notifications/run%3Anvda%3Acompleted/read")
    unread = client.get("/api/notifications", params={"unread_only": "true"})

    assert mark.status_code == 200
    assert mark.json()["updated"] == 1
    assert mark.json()["unread_count"] == 0
    assert unread.status_code == 200
    assert unread.json()["items"] == []


def test_notification_center_can_mark_all_read(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "alerts": {"rules": [{"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy", "created_at": "2026-01-15T00:30:00"}]},
        "notifications": {"read_items": []},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "save_settings", lambda settings, path=None: state.update(settings))

    run = _make_run("nvda")
    run.ticker = "NVDA"
    run.signal = "Buy"
    run.status = "completed"
    run.created_at = "2026-01-15T02:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run if run_id == "nvda" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.post("/api/notifications/read-all")

    assert response.status_code == 200
    assert response.json()["updated"] == 2
    assert response.json()["unread_count"] == 0
    assert len(state["notifications"]["read_items"]) == 2


def test_notification_center_mark_all_read_respects_kind_filter(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "alerts": {"rules": [{"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy", "created_at": "2026-01-15T00:30:00"}]},
        "notifications": {"read_items": []},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "save_settings", lambda settings, path=None: state.update(settings))

    run = _make_run("nvda")
    run.ticker = "NVDA"
    run.signal = "Buy"
    run.status = "completed"
    run.created_at = "2026-01-15T02:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run if run_id == "nvda" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.post("/api/notifications/read-all", params={"kind": "alert"})

    assert response.status_code == 200
    assert response.json()["updated"] == 1
    assert response.json()["unread_count"] == 1
    assert [item["id"] for item in state["notifications"]["read_items"]] == ["alert:rule-buy:nvda"]


def test_notification_center_export_csv_respects_filters(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "alerts": {"rules": [{"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy", "created_at": "2026-01-15T00:30:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run = _make_run("nvda")
    run.ticker = "NVDA"
    run.signal = "Buy"
    run.status = "completed"
    run.created_at = "2026-01-15T02:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run if run_id == "nvda" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/notifications/export", params={"kind": "alert"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "tradingagents-notifications-default-" in response.headers["content-disposition"]
    assert "id,kind,severity,title,message,created_at,is_read,member,ticker,run_id,target_url" in response.text
    assert "alert:rule-buy:nvda,alert,warning,Alert hit for NVDA" in response.text
    assert ",run,info,NVDA run completed," not in response.text


def test_dashboard_hides_snoozed_pinned_actions(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "pinned_runs": {
            "items": [
                {"run_id": "nvda", "note": "Core thesis", "category": "high-conviction", "priority": "p1", "next_action": "Review after earnings", "action_status": "todo", "due_date": "2099-01-20", "snoozed_until": "2099-01-19", "created_at": "2026-01-15T02:00:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    response = client.get("/api/dashboard")

    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"]["pinned_action_count"] == 0
    assert payload["pinned_actions"] == []


def test_dashboard_preferences_patch_persists_visible_sections(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"dashboard": {"visible_sections": ["bullish_focus"], "section_order": ["bullish_focus", "needs_attention"]}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.patch(
        "/api/dashboard/preferences",
        json={"visible_sections": ["active_alerts", "portfolio_focus"], "section_order": ["portfolio_focus", "active_alerts"]},
    )

    assert response.status_code == 200
    assert response.json()["visible_sections"] == ["active_alerts", "portfolio_focus"]
    assert response.json()["section_order"] == ["portfolio_focus", "active_alerts"]
    assert state["dashboard"]["visible_sections"] == ["active_alerts", "portfolio_focus"]
    assert state["dashboard"]["section_order"] == ["portfolio_focus", "active_alerts"]


def test_workspace_export_json_returns_workspace_snapshot(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"ticker": "NVDA", "created_at": "2026-01-15T02:00:00"}]},
        "alerts": {"rules": [{"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy", "created_at": "2026-01-15T02:05:00"}]},
        "portfolio": {"positions": [{"id": "pos-a", "ticker": "NVDA", "quantity": 10, "average_cost": 100.0, "created_at": "2026-01-15T02:10:00"}]},
        "workspace": {"default_home_view": "saved-view", "default_saved_view_id": "view-1"},
        "dashboard": {"visible_sections": ["bullish_focus", "portfolio_focus"], "section_order": ["portfolio_focus", "bullish_focus"]},
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-15T01:55:00"}]},
        "run_comments": {"items": [{"id": "comment-a", "run_id": "nvda", "author": "Alice", "content": "Looks good.", "created_at": "2026-01-15T02:12:00", "resolved": False}]},
        "run_reviews": {"items": [{"run_id": "nvda", "reviewer": "Alice", "status": "pending", "note": "Check the downside case.", "created_at": "2026-01-15T02:13:00", "updated_at": "2026-01-15T02:14:00"}]},
        "pinned_runs": {"items": [{"run_id": "nvda", "note": "Core thesis", "category": "high-conviction", "priority": "p1", "next_action": "Review after earnings", "action_status": "todo", "created_at": "2026-01-15T02:15:00"}]},
        "notes": {"items": [{"id": "note-1", "content": "Watch guidance drift", "tags": ["earnings"], "ticker": "NVDA", "run_id": "nvda", "created_at": "2026-01-15T02:20:00", "updated_at": "2026-01-15T02:20:00"}]},
        "presets": {"items": [{"id": "preset-1", "name": "Growth Deep Dive", "created_at": "2026-01-15T02:25:00", "analysis_request": {"ticker": "NVDA", "llm_provider": "openai", "research_depth": 5}}]},
        "saved_searches": {"items": [{"id": "search-1", "name": "Bullish NVDA", "query": "NVDA buy", "kinds": ["run", "note"], "created_at": "2026-01-15T02:30:00"}]},
        "saved_views": {"items": [{"id": "view-1", "name": "Morning Focus", "url": "/?view=briefing", "visible_panels": ["dashboard-panel"], "created_at": "2026-01-15T02:35:00"}]},
        "run_annotations": {"items": [{"run_id": "nvda", "label": "High conviction", "summary": "Keep through earnings", "next_step": "Recheck on close", "created_at": "2026-01-15T02:40:00", "updated_at": "2026-01-15T02:45:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    nvda = _make_run("nvda")
    nvda.ticker = "NVDA"
    nvda.signal = "Buy"
    nvda.status = "completed"
    nvda.created_at = "2026-01-15T01:00:00"
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [nvda])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: nvda if run_id == "nvda" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/workspace/export", headers={"X-TradingAgents-Tenant": "desk-a"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "tradingagents-workspace-desk-a-" in response.headers["content-disposition"]
    payload = response.json()
    assert payload["summary"]["tenant_id"] == "desk-a"
    assert payload["summary"]["run_count"] == 1
    assert payload["summary"]["watchlist_count"] == 1
    assert payload["summary"]["alert_hit_count"] == 1
    assert payload["watchlist"][0]["ticker"] == "NVDA"
    assert payload["alerts"]["rules"][0]["id"] == "rule-buy"
    assert payload["portfolio"]["positions"][0]["ticker"] == "NVDA"
    assert payload["action_board"]["todo"][0]["run_id"] == "nvda"
    assert payload["saved_views"][0]["name"] == "Morning Focus"
    assert payload["annotations"][0]["label"] == "High conviction"
    assert payload["workspace_settings"]["default_home_view"] == "saved-view"
    assert payload["dashboard_preferences"]["section_order"] == ["portfolio_focus", "bullish_focus"]
    assert payload["workspace_members"][0]["name"] == "Alice"
    assert payload["run_comments"][0]["id"] == "comment-a"
    assert payload["run_reviews"][0]["reviewer"] == "Alice"


def test_workspace_export_markdown_returns_handoff_summary(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"ticker": "NVDA", "created_at": "2026-01-15T02:00:00"}]},
        "alerts": {"rules": [{"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy", "created_at": "2026-01-15T02:05:00"}]},
        "portfolio": {"positions": [{"id": "pos-a", "ticker": "NVDA", "quantity": 10, "average_cost": 100.0, "created_at": "2026-01-15T02:10:00"}]},
        "pinned_runs": {"items": [{"run_id": "nvda", "note": "Core thesis", "category": "high-conviction", "priority": "p1", "next_action": "Review after earnings", "action_status": "todo", "due_date": "2026-01-20", "created_at": "2026-01-15T02:15:00"}]},
        "notes": {"items": [{"id": "note-1", "content": "Watch guidance drift into the close.", "tags": ["earnings"], "ticker": "NVDA", "run_id": "nvda", "created_at": "2026-01-15T02:20:00", "updated_at": "2026-01-15T02:20:00"}]},
        "run_annotations": {"items": [{"run_id": "nvda", "label": "High conviction", "summary": "Keep through earnings", "next_step": "Recheck on close", "created_at": "2026-01-15T02:40:00", "updated_at": "2026-01-15T02:45:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    nvda = _make_run("nvda")
    nvda.ticker = "NVDA"
    nvda.signal = "Buy"
    nvda.status = "completed"
    nvda.created_at = "2026-01-15T01:00:00"
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [nvda])
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: nvda if run_id == "nvda" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/workspace/export", params={"format": "markdown"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
    assert "# TradingAgents Workspace Export" in response.text
    assert "## Snapshot" in response.text
    assert "## Recent Runs" in response.text
    assert "## Pinned Actions" in response.text
    assert "Rule: NVDA signal = Buy" in response.text
    assert "High conviction" in response.text


def test_workspace_import_replace_restores_snapshot_buckets(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"ticker": "AAPL", "created_at": "2026-01-10T01:00:00"}]},
        "alerts": {"rules": [{"id": "rule-old", "ticker": "AAPL", "field": "signal", "value": "Hold", "created_at": "2026-01-10T01:05:00"}]},
        "portfolio": {"positions": [{"id": "pos-old", "ticker": "AAPL", "quantity": 1, "average_cost": 100.0, "created_at": "2026-01-10T01:10:00"}]},
        "workspace": {"default_home_view": "dashboard"},
        "dashboard": {"visible_sections": ["bullish_focus"], "section_order": ["bullish_focus", "needs_attention"]},
        "workspace_members": {"items": [{"id": "member-old", "name": "Bob", "created_at": "2026-01-10T01:15:00"}]},
        "run_comments": {"items": [{"id": "comment-old", "run_id": "aapl", "author": "Bob", "content": "Old comment", "created_at": "2026-01-10T01:20:00", "resolved": False}]},
        "run_reviews": {"items": [{"run_id": "aapl", "reviewer": "Bob", "status": "approved", "note": "done", "created_at": "2026-01-10T01:25:00", "updated_at": "2026-01-10T01:26:00"}]},
        "pinned_runs": {"items": [{"run_id": "aapl", "note": "Old pin", "created_at": "2026-01-10T01:30:00"}]},
        "notes": {"items": [{"id": "note-old", "content": "Old note", "tags": ["old"], "ticker": "AAPL", "created_at": "2026-01-10T01:35:00", "updated_at": "2026-01-10T01:35:00"}]},
        "presets": {"items": [{"id": "preset-old", "name": "Legacy", "created_at": "2026-01-10T01:40:00", "analysis_request": {"ticker": "AAPL", "llm_provider": "openai"}}]},
        "saved_searches": {"items": [{"id": "search-old", "name": "Old Search", "query": "AAPL", "kinds": ["run"], "created_at": "2026-01-10T01:45:00"}]},
        "saved_views": {"items": [{"id": "view-old", "name": "Old View", "url": "/?ticker=AAPL", "visible_panels": ["history-panel"], "created_at": "2026-01-10T01:50:00"}]},
        "run_annotations": {"items": [{"run_id": "aapl", "label": "Old", "created_at": "2026-01-10T01:55:00", "updated_at": "2026-01-10T01:56:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    snapshot = {
        "summary": {"exported_at": "2026-01-20T09:00:00", "tenant_id": "desk-a"},
        "workspace_settings": {"default_home_view": "saved-view", "default_saved_view_id": "view-1"},
        "dashboard_preferences": {"visible_sections": ["portfolio_focus"], "section_order": ["portfolio_focus", "bullish_focus"]},
        "watchlist": [{"ticker": "NVDA", "created_at": "2026-01-20T09:01:00", "run_count": 0}],
        "alerts": {"rules": [{"id": "rule-buy", "ticker": "NVDA", "field": "signal", "value": "Buy", "created_at": "2026-01-20T09:02:00"}], "hits": []},
        "portfolio": {"summary": {"position_count": 1, "unique_ticker_count": 1, "total_cost_basis": 300.0, "signal_breakdown": {}}, "positions": [{"id": "pos-a", "ticker": "NVDA", "quantity": 2, "average_cost": 150.0, "cost_basis": 300.0, "created_at": "2026-01-20T09:03:00"}]},
        "workspace_members": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-20T09:04:00"}],
        "run_comments": [{"id": "comment-a", "run_id": "nvda", "author": "Alice", "content": "Check earnings timing", "created_at": "2026-01-20T09:05:00", "resolved": False}],
        "run_reviews": [{"run_id": "nvda", "reviewer": "Alice", "status": "pending", "note": "Review downside case", "created_at": "2026-01-20T09:06:00", "updated_at": "2026-01-20T09:07:00"}],
        "pinned_runs": [{"run_id": "nvda", "ticker": "NVDA", "note": "Core thesis", "created_at": "2026-01-20T09:08:00"}],
        "action_board": {"todo": [], "doing": [], "done": []},
        "timeline": {"events": []},
        "notes": [{"id": "note-1", "content": "Watch guidance drift", "tags": ["earnings"], "ticker": "NVDA", "run_id": "nvda", "created_at": "2026-01-20T09:09:00", "updated_at": "2026-01-20T09:09:00"}],
        "presets": [{"id": "preset-1", "name": "Growth", "created_at": "2026-01-20T09:10:00", "analysis_request": {"ticker": "NVDA", "llm_provider": "openai", "research_depth": 5}}],
        "saved_searches": [{"id": "search-1", "name": "Bullish NVDA", "query": "NVDA buy", "kinds": ["run", "note"], "created_at": "2026-01-20T09:11:00"}],
        "saved_views": [{"id": "view-1", "name": "Morning Focus", "url": "/?view=briefing", "visible_panels": ["dashboard-panel"], "created_at": "2026-01-20T09:12:00"}],
        "annotations": [{"run_id": "nvda", "label": "High conviction", "summary": "Keep through earnings", "next_step": "Recheck on close", "created_at": "2026-01-20T09:13:00", "updated_at": "2026-01-20T09:14:00"}],
        "runs": [],
    }

    response = client.post("/api/workspace/import", json={"content": json.dumps(snapshot), "mode": "replace"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "replace"
    assert payload["watchlist_count"] == 1
    assert payload["member_count"] == 1
    assert payload["review_count"] == 1
    assert [item["ticker"] for item in state["watchlist"]["tickers"]] == ["NVDA"]
    assert state["workspace"]["default_home_view"] == "saved-view"
    assert state["dashboard"]["section_order"] == ["portfolio_focus", "bullish_focus"]
    assert [item["name"] for item in state["workspace_members"]["items"]] == ["Alice"]
    assert [item["id"] for item in state["run_comments"]["items"]] == ["comment-a"]
    assert [item["run_id"] for item in state["run_reviews"]["items"]] == ["nvda"]
    assert [item["run_id"] for item in state["run_annotations"]["items"]] == ["nvda"]


def test_workspace_import_merge_preserves_existing_state_and_adds_snapshot_items(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"ticker": "AAPL", "created_at": "2026-01-10T01:00:00"}]},
        "workspace": {"default_home_view": "dashboard"},
        "dashboard": {"visible_sections": ["bullish_focus"], "section_order": ["bullish_focus", "needs_attention"]},
        "workspace_members": {"items": [{"id": "member-old", "name": "Bob", "created_at": "2026-01-10T01:15:00"}]},
        "notes": {"items": [{"id": "note-old", "content": "Old note", "tags": ["old"], "ticker": "AAPL", "created_at": "2026-01-10T01:35:00", "updated_at": "2026-01-10T01:35:00"}]},
        "saved_views": {"items": [{"id": "view-old", "name": "Old View", "url": "/?ticker=AAPL", "visible_panels": ["history-panel"], "created_at": "2026-01-10T01:50:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    snapshot = {
        "summary": {"exported_at": "2026-01-20T09:00:00"},
        "workspace_settings": {"default_home_view": "saved-view", "default_saved_view_id": "view-1"},
        "dashboard_preferences": {"visible_sections": ["portfolio_focus"], "section_order": ["portfolio_focus", "bullish_focus"]},
        "watchlist": [
            {"ticker": "AAPL", "created_at": "2026-01-20T09:01:00", "run_count": 0},
            {"ticker": "NVDA", "created_at": "2026-01-20T09:02:00", "run_count": 0},
        ],
        "alerts": {"rules": [], "hits": []},
        "portfolio": {"summary": {"position_count": 0, "unique_ticker_count": 0, "total_cost_basis": 0.0, "signal_breakdown": {}}, "positions": []},
        "workspace_members": [
            {"id": "member-old", "name": "Bob", "created_at": "2026-01-10T01:15:00"},
            {"id": "member-a", "name": "Alice", "created_at": "2026-01-20T09:04:00"},
        ],
        "run_comments": [],
        "run_reviews": [],
        "pinned_runs": [],
        "action_board": {"todo": [], "doing": [], "done": []},
        "timeline": {"events": []},
        "notes": [{"id": "note-new", "content": "New note", "tags": ["new"], "ticker": "NVDA", "created_at": "2026-01-20T09:09:00", "updated_at": "2026-01-20T09:09:00"}],
        "presets": [],
        "saved_searches": [],
        "saved_views": [{"id": "view-1", "name": "Morning Focus", "url": "/?view=briefing", "visible_panels": ["dashboard-panel"], "created_at": "2026-01-20T09:12:00"}],
        "annotations": [],
        "runs": [],
    }

    response = client.post("/api/workspace/import", json={"content": json.dumps(snapshot), "mode": "merge"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "merge"
    assert payload["watchlist_count"] == 2
    assert payload["member_count"] == 2
    assert [item["ticker"] for item in state["watchlist"]["tickers"]] == ["AAPL", "NVDA"]
    assert state["workspace"]["default_home_view"] == "saved-view"
    assert [item["name"] for item in state["workspace_members"]["items"]] == ["Bob", "Alice"]
    assert [item["id"] for item in state["notes"]["items"]] == ["note-old", "note-new"]
    assert [item["id"] for item in state["saved_views"]["items"]] == ["view-old", "view-1"]


def test_presets_endpoint_returns_saved_presets(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "presets": {
            "items": [
                {
                    "id": "preset-a",
                    "name": "China Swing",
                    "analysis_request": {
                        "ticker": "600519.SS",
                        "llm_provider": "openai",
                        "research_depth": 5,
                        "market_profile": "cn_a",
                        "output_language": "Chinese",
                    },
                }
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    response = client.get("/api/presets")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["id"] == "preset-a"
    assert payload[0]["name"] == "China Swing"
    assert payload[0]["analysis_request"]["market_profile"] == "cn_a"


def test_preset_post_adds_saved_configuration(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"presets": {"items": []}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post(
        "/api/presets",
        json={
            "name": "US Momentum",
            "analysis_request": {
                "ticker": "NVDA",
                "llm_provider": "openai",
                "research_depth": 3,
                "output_language": "English",
                "market_profile": "default",
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["name"] == "US Momentum"
    assert payload["analysis_request"]["ticker"] == "NVDA"
    assert len(state["presets"]["items"]) == 1


def test_preset_delete_removes_saved_configuration(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "presets": {
            "items": [
                {"id": "preset-a", "name": "One", "analysis_request": {"ticker": "AAPL"}},
                {"id": "preset-b", "name": "Two", "analysis_request": {"ticker": "NVDA"}},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.delete("/api/presets/preset-b")

    assert response.status_code == 200
    assert response.json() == {"deleted": 1}
    assert [item["id"] for item in state["presets"]["items"]] == ["preset-a"]


def test_preset_update_can_rename(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "presets": {
            "items": [
                {"id": "preset-a", "name": "US Momentum", "analysis_request": {"ticker": "NVDA"}},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.patch("/api/presets/preset-a", json={"name": "US Momentum Core"})

    assert response.status_code == 200
    assert response.json()["name"] == "US Momentum Core"


def test_preset_duplicate_creates_copy(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "presets": {
            "items": [
                {"id": "preset-a", "name": "US Momentum", "analysis_request": {"ticker": "NVDA", "llm_provider": "openai"}},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post("/api/presets/preset-a/duplicate")

    assert response.status_code == 201
    assert response.json()["name"] == "US Momentum Copy"
    assert response.json()["analysis_request"]["ticker"] == "NVDA"
    assert len(state["presets"]["items"]) == 2


def test_notes_endpoint_filters_by_ticker_and_run(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "notes": {
            "items": [
                {"id": "note-a", "content": "Watch policy risk.", "ticker": "NVDA", "run_id": None, "created_at": "2026-01-10T09:00:00", "updated_at": "2026-01-10T09:00:00"},
                {"id": "note-b", "content": "This run missed the catalyst.", "ticker": "NVDA", "run_id": "run-1", "created_at": "2026-01-11T09:00:00", "updated_at": "2026-01-11T09:00:00"},
                {"id": "note-c", "content": "Ignore.", "ticker": "AAPL", "run_id": None, "created_at": "2026-01-12T09:00:00", "updated_at": "2026-01-12T09:00:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    ticker_response = client.get("/api/notes", params={"ticker": "NVDA"})
    run_response = client.get("/api/notes", params={"run_id": "run-1"})

    assert ticker_response.status_code == 200
    assert [item["id"] for item in ticker_response.json()] == ["note-b", "note-a"]
    assert run_response.status_code == 200
    assert [item["id"] for item in run_response.json()] == ["note-b"]


def test_notes_endpoint_searches_content_and_tags(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "notes": {
            "items": [
                {"id": "note-a", "content": "Watch policy risk.", "tags": ["macro", "risk"], "ticker": "NVDA", "run_id": None, "created_at": "2026-01-10T09:00:00", "updated_at": "2026-01-10T09:00:00"},
                {"id": "note-b", "content": "This run missed the catalyst.", "tags": ["earnings"], "ticker": "NVDA", "run_id": "run-1", "created_at": "2026-01-11T09:00:00", "updated_at": "2026-01-11T09:00:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    response = client.get("/api/notes", params={"ticker": "NVDA", "q": "macro"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == ["note-a"]


def test_run_comments_round_trip_and_require_workspace_members(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-10T08:00:00"}]},
        "run_comments": {"items": []},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: _make_run("run-a") if run_id == "run-a" else None)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    create = client.post("/api/runs/run-a/comments", json={"author": "Alice", "content": "We should revisit guidance assumptions."})
    listed = client.get("/api/runs/run-a/comments")
    deleted = client.delete(f"/api/runs/run-a/comments/{create.json()['id']}")

    assert create.status_code == 201
    assert create.json()["author"] == "Alice"
    assert listed.status_code == 200
    assert listed.json()[0]["content"] == "We should revisit guidance assumptions."
    assert deleted.status_code == 200
    assert deleted.json()["deleted"] == 1


def test_run_comment_can_be_resolved_and_reopened(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-10T08:00:00"}]},
        "run_comments": {
            "items": [
                {"id": "comment-a", "run_id": "run-a", "author": "Alice", "content": "Please verify the catalyst timing.", "created_at": "2026-01-15T10:00:00"}
            ]
        },
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: _make_run("run-a"))

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    resolved = client.patch("/api/runs/run-a/comments/comment-a", json={"resolved": True, "resolved_by": "Alice"})
    reopened = client.patch("/api/runs/run-a/comments/comment-a", json={"resolved": False})

    assert resolved.status_code == 200
    assert resolved.json()["resolved"] is True
    assert resolved.json()["resolved_by"] == "Alice"
    assert resolved.json()["resolved_at"] is not None
    assert reopened.status_code == 200
    assert reopened.json()["resolved"] is False
    assert reopened.json()["resolved_by"] is None
    assert reopened.json()["resolved_at"] is None


def test_run_comment_post_rejects_unknown_member(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"workspace_members": {"items": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-10T08:00:00"}]}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: _make_run("run-a"))

    response = client.post("/api/runs/run-a/comments", json={"author": "Bob", "content": "Unknown author should fail."})

    assert response.status_code == 400
    assert response.json()["detail"] == "Author must match a saved workspace member"


def test_run_comment_resolve_requires_known_member(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-10T08:00:00"}]},
        "run_comments": {"items": [{"id": "comment-a", "run_id": "run-a", "author": "Alice", "content": "Please verify the catalyst timing.", "created_at": "2026-01-15T10:00:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: _make_run("run-a"))

    response = client.patch("/api/runs/run-a/comments/comment-a", json={"resolved": True, "resolved_by": "Bob"})

    assert response.status_code == 400
    assert response.json()["detail"] == "resolved_by must match a saved workspace member"


def test_run_review_round_trip(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-10T08:00:00"}]},
        "run_reviews": {"items": []},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: _make_run("run-a") if run_id == "run-a" else None)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    create = client.post("/api/runs/run-a/review", json={"reviewer": "Alice", "status": "pending", "note": "Check the downside case."})
    delete = client.delete("/api/runs/run-a/review")

    assert create.status_code == 201
    assert create.json()["reviewer"] == "Alice"
    assert create.json()["status"] == "pending"
    assert create.json()["note"] == "Check the downside case."
    assert delete.status_code == 200
    assert delete.json()["deleted"] == 1


def test_run_review_history_filters_by_reviewer_and_status(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "run_reviews": {
            "items": [
                {"run_id": "run-a", "reviewer": "Alice", "status": "pending", "note": "Check downside case.", "created_at": "2026-01-15T10:00:00", "updated_at": "2026-01-15T10:10:00"},
                {"run_id": "run-b", "reviewer": "Bob", "status": "approved", "note": "Looks good.", "created_at": "2026-01-14T10:00:00", "updated_at": "2026-01-14T10:10:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run_a = _make_run("run-a")
    run_a.ticker = "NVDA"
    run_a.signal = "Buy"
    run_b = _make_run("run-b")
    run_b.ticker = "AAPL"
    run_b.signal = "Hold"
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run_a, run_b])

    response = client.get("/api/reviews", params={"reviewer": "Alice", "status": "pending"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["reviewer_filter"] == "Alice"
    assert payload["status_filter"] == "pending"
    assert payload["summary"]["total_reviews"] == 1
    assert payload["summary"]["pending_count"] == 1
    assert payload["items"][0]["run_id"] == "run-a"
    assert payload["items"][0]["ticker"] == "NVDA"


def test_run_review_history_export_csv_respects_filters(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "run_reviews": {
            "items": [
                {"run_id": "run-a", "reviewer": "Alice", "status": "pending", "note": "Check downside case.", "created_at": "2026-01-15T10:00:00", "updated_at": "2026-01-15T10:10:00"},
                {"run_id": "run-b", "reviewer": "Bob", "status": "approved", "note": "Looks good.", "created_at": "2026-01-14T10:00:00", "updated_at": "2026-01-14T10:10:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run_a = _make_run("run-a")
    run_a.ticker = "NVDA"
    run_a.signal = "Buy"
    run_b = _make_run("run-b")
    run_b.ticker = "AAPL"
    run_b.signal = "Hold"
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run_a, run_b])

    response = client.get("/api/reviews/export", params={"reviewer": "Alice", "status": "pending"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "tradingagents-review-history-default-" in response.headers["content-disposition"]
    assert "run_id,reviewer,status,note,created_at,updated_at,ticker,date,signal" in response.text
    assert "run-a,Alice,pending,Check downside case.,2026-01-15T10:00:00,2026-01-15T10:10:00,NVDA,2026-01-15,Buy" in response.text
    assert "run-b" not in response.text


def test_workspace_search_can_find_comments_and_reviews(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "run_comments": {
            "items": [
                {"id": "comment-a", "run_id": "run-a", "author": "Alice", "content": "Need to revisit the downside case.", "created_at": "2026-01-15T10:00:00"}
            ]
        },
        "run_reviews": {
            "items": [
                {"run_id": "run-a", "reviewer": "Bob", "status": "changes_requested", "note": "Rework the valuation section.", "created_at": "2026-01-15T11:00:00", "updated_at": "2026-01-15T11:10:00"}
            ]
        },
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: _make_run("run-a") if run_id == "run-a" else None)

    response = client.get("/api/search", params={"q": "valuation", "kinds": "comment,review"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_kinds"] == ["comment", "review"]
    assert [item["kind"] for item in payload["results"]] == ["review"]

    response_comments = client.get("/api/search", params={"q": "downside", "kinds": "comment,review"})
    assert response_comments.status_code == 200
    payload_comments = response_comments.json()
    assert payload_comments["active_kinds"] == ["comment", "review"]
    assert [item["kind"] for item in payload_comments["results"]] == ["comment"]


def test_note_post_adds_saved_note(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"notes": {"items": []}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post(
        "/api/notes",
        json={"content": "Need to revisit after earnings.", "ticker": " nvda ", "run_id": "run-1"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["ticker"] == "NVDA"
    assert payload["run_id"] == "run-1"
    assert payload["content"] == "Need to revisit after earnings."
    assert payload["tags"] == []
    assert len(state["notes"]["items"]) == 1


def test_note_put_updates_content_and_tags(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "notes": {
            "items": [
                {"id": "note-a", "content": "Old note", "tags": ["old"], "ticker": "NVDA", "run_id": None, "created_at": "2026-01-10T09:00:00", "updated_at": "2026-01-10T09:00:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.put(
        "/api/notes/note-a",
        json={"content": "Updated note", "tags": ["macro", "risk"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["content"] == "Updated note"
    assert payload["tags"] == ["macro", "risk"]
    assert state["notes"]["items"][0]["content"] == "Updated note"


def test_note_delete_removes_saved_note(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "notes": {
            "items": [
                {"id": "note-a", "content": "One", "ticker": "AAPL", "run_id": None, "created_at": "2026-01-10T09:00:00", "updated_at": "2026-01-10T09:00:00"},
                {"id": "note-b", "content": "Two", "ticker": "NVDA", "run_id": "run-1", "created_at": "2026-01-11T09:00:00", "updated_at": "2026-01-11T09:00:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.delete("/api/notes/note-b")

    assert response.status_code == 200
    assert response.json() == {"deleted": 1}
    assert [item["id"] for item in state["notes"]["items"]] == ["note-a"]


def test_workspace_timeline_returns_saved_events_in_reverse_chronological_order(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"id": "watch-a", "ticker": "NVDA", "created_at": "2026-01-12T09:00:00"}]},
        "alerts": {"rules": [{"id": "alert-a", "ticker": "NVDA", "field": "signal", "value": "Buy", "created_at": "2026-01-13T09:00:00"}]},
        "portfolio": {"positions": [{"id": "pos-a", "ticker": "NVDA", "quantity": 10, "average_cost": 100.0, "created_at": "2026-01-14T09:00:00"}]},
        "presets": {"items": [{"id": "preset-a", "name": "Momentum", "created_at": "2026-01-15T09:00:00", "analysis_request": {"ticker": "NVDA"}}]},
        "notes": {"items": [{"id": "note-a", "content": "Need to revisit margins.", "ticker": "NVDA", "run_id": None, "created_at": "2026-01-15T12:00:00", "updated_at": "2026-01-15T12:00:00"}]},
        "run_annotations": {"items": [{"run_id": "run-a", "label": "High Conviction", "summary": "Best setup", "next_step": "Review after earnings", "created_at": "2026-01-15T18:00:00", "updated_at": "2026-01-15T18:00:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run = _make_run("run-a")
    run.ticker = "NVDA"
    run.signal = "Buy"
    run.status = "completed"
    run.date = "2026-01-16"
    run.created_at = "2026-01-16T09:00:00"
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/timeline")

    assert response.status_code == 200
    payload = response.json()
    assert [event["kind"] for event in payload["events"][:7]] == [
        "run",
        "annotation",
        "note",
        "preset",
        "portfolio",
        "alert",
        "watchlist",
    ]
    assert payload["events"][0]["run_id"] == "run-a"
    assert payload["events"][1]["title"] == "Run annotated: NVDA"


def test_workspace_timeline_can_filter_by_kinds(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"id": "watch-a", "ticker": "NVDA", "created_at": "2026-01-12T09:00:00"}]},
        "alerts": {"rules": [{"id": "alert-a", "ticker": "NVDA", "field": "signal", "value": "Buy", "created_at": "2026-01-13T09:00:00"}]},
        "notes": {"items": [{"id": "note-a", "content": "Need to revisit margins.", "ticker": "NVDA", "run_id": None, "created_at": "2026-01-15T12:00:00", "updated_at": "2026-01-15T12:00:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/timeline", params={"kinds": "note,alert"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_kinds"] == ["note", "alert"]
    assert [event["kind"] for event in payload["events"]] == ["note", "alert"]


def test_workspace_timeline_can_include_run_comments(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "run_comments": {"items": [{"id": "comment-a", "run_id": "run-a", "author": "Alice", "content": "Revisit the valuation framing.", "created_at": "2026-01-15T12:00:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    response = client.get("/api/timeline", params={"kinds": "comment"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_kinds"] == ["comment"]
    assert payload["events"][0]["kind"] == "comment"
    assert payload["events"][0]["title"] == "Comment from Alice"


def test_workspace_timeline_can_include_saved_searches_views_members_and_public_shares(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "saved_searches": {"items": [{"id": "search-a", "name": "Risk Notes", "query": "risk", "kinds": ["note"], "created_at": "2026-01-15T08:00:00"}]},
        "saved_views": {"items": [{"id": "view-a", "name": "Morning Focus", "url": "/?view=briefing", "visible_panels": ["dashboard-panel"], "created_at": "2026-01-15T09:00:00"}]},
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "role": "reviewer", "created_at": "2026-01-15T10:00:00"}]},
        "public_run_shares": {"items": [{"share_id": "share-a", "tenant_id": None, "run_id": "run-a", "ticker": "NVDA", "date": "2026-01-15", "asset_type": "stock", "status": "completed", "created_at": "2026-01-15T11:00:00", "signal": "Buy", "view_count": 2, "last_viewed_at": "2026-01-15T12:00:00", "config_summary": {}, "report_sections": {}, "current_report": None, "final_report": "Report", "annotation": None, "review": None}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    response = client.get("/api/timeline", params={"kinds": "search,view,member,share"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_kinds"] == ["search", "view", "member", "share"]
    assert [event["kind"] for event in payload["events"]] == ["share", "member", "view", "search"]
    assert payload["events"][0]["title"] == "Public snapshot shared for NVDA"
    assert payload["events"][1]["title"] == "Workspace member added: Alice"


def test_workspace_timeline_export_csv_returns_filtered_events(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"id": "watch-a", "ticker": "NVDA", "created_at": "2026-01-12T09:00:00"}]},
        "notes": {"items": [{"id": "note-a", "content": "Need to revisit margins.", "ticker": "NVDA", "run_id": None, "created_at": "2026-01-15T12:00:00", "updated_at": "2026-01-15T12:00:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    response = client.get("/api/timeline/export", params={"kinds": "note"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "tradingagents-workspace-timeline-default-" in response.headers["content-disposition"]
    assert "kind,occurred_at,title,detail,ticker,run_id" in response.text
    assert "note,2026-01-15T12:00:00,Note saved for NVDA,Need to revisit margins.,NVDA," in response.text
    assert "watchlist" not in response.text


def test_workspace_calendar_groups_events_by_date(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"id": "watch-a", "ticker": "NVDA", "created_at": "2026-01-12T09:00:00"}]},
        "notes": {"items": [{"id": "note-a", "content": "Need to revisit margins.", "ticker": "NVDA", "run_id": None, "created_at": "2026-01-12T12:00:00", "updated_at": "2026-01-12T12:00:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run = _make_run("run-a")
    run.ticker = "NVDA"
    run.signal = "Buy"
    run.status = "completed"
    run.date = "2026-01-13"
    run.created_at = "2026-01-13T09:00:00"
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/calendar")

    assert response.status_code == 200
    payload = response.json()
    assert payload["days"][0]["date"] == "2026-01-13"
    assert payload["days"][0]["events"][0]["kind"] == "run"
    assert payload["days"][1]["date"] == "2026-01-12"
    assert [event["kind"] for event in payload["days"][1]["events"]] == ["note", "watchlist"]


def test_share_run_link_includes_run_id_and_tenant_scope(monkeypatch):
    client = TestClient(app)
    run = _make_run("share-run")
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run)

    response = client.get(
        f"/api/share/runs/{run.run_id}",
        headers={"X-TradingAgents-Tenant": "tenant-a"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["label"] == "Run Link"
    assert "run_id=share-run" in payload["url"]
    assert "tenant_id=tenant-a" in payload["url"]


def test_share_ticker_link_normalizes_ticker(monkeypatch):
    client = TestClient(app)

    response = client.get("/api/share/tickers/nvda")

    assert response.status_code == 200
    payload = response.json()
    assert payload["label"] == "Ticker Link"
    assert payload["url"] == "/?ticker=NVDA"


def test_share_compare_link_includes_both_runs(monkeypatch):
    client = TestClient(app)

    response = client.get("/api/share/compare", params={"left_run_id": "left", "right_run_id": "right"})

    assert response.status_code == 200
    payload = response.json()
    assert "compare_left_run_id=left" in payload["url"]
    assert "compare_right_run_id=right" in payload["url"]


def test_share_briefing_link_targets_briefing_view():
    client = TestClient(app)

    response = client.get("/api/share/briefing/daily")

    assert response.status_code == 200
    payload = response.json()
    assert payload["label"] == "Briefing Link"
    assert payload["url"] == "/?view=briefing"


def test_public_run_share_create_returns_public_url_and_persists_snapshot(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {}
    run = _make_run("share-run")
    run.ticker = "NVDA"
    run.status = "completed"
    run.signal = "Buy"
    run.created_at = "2026-01-15T09:00:00"
    run.report_sections["final_trade_decision"] = "Rating: Buy"
    run.final_report = "# Trading Analysis Report\n\nBull case is stronger than bear case."

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run if run_id == "share-run" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post("/api/runs/share-run/public-share", headers={"X-TradingAgents-Tenant": "tenant-a"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["share_id"]
    assert payload["url"].endswith(f"/shared/{payload['share_id']}")
    assert payload["created_at"]
    assert state["public_run_shares"]["items"][0]["run_id"] == "share-run"
    assert state["public_run_shares"]["items"][0]["ticker"] == "NVDA"
    assert state["public_run_shares"]["items"][0]["tenant_id"] == "tenant-a"
    assert state["public_run_shares"]["items"][0]["view_count"] == 0
    assert state["public_run_shares"]["items"][0]["last_viewed_at"] is None
    assert state["public_run_shares"]["items"][0]["expires_at"] is None
    assert state["public_run_shares"]["items"][0]["share_title"] is None
    assert state["public_run_shares"]["items"][0]["share_summary"] is None


def test_public_run_share_create_reuses_existing_share_for_same_run(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "public_run_shares": {
            "items": [
                {
                    "share_id": "share-abc123",
                    "tenant_id": "tenant-a",
                    "run_id": "share-run",
                    "ticker": "NVDA",
                    "date": "2026-01-15",
                    "asset_type": "stock",
                    "status": "completed",
                    "created_at": "2026-01-15T10:00:00",
                    "signal": "Buy",
                    "error": None,
                    "config_summary": {},
                    "report_sections": {"final_trade_decision": "Rating: Buy"},
                    "current_report": None,
                    "final_report": "# Trading Analysis Report\n\nOld share.",
                    "view_count": 3,
                    "last_viewed_at": "2026-01-15T11:00:00",
                    "expires_at": "2026-01-20T10:00:00",
                    "share_title": "NVDA Snapshot",
                    "share_summary": "External summary",
                    "annotation": None,
                    "review": None,
                }
            ]
        }
    }
    run = _make_run("share-run")
    run.ticker = "NVDA"
    run.status = "completed"
    run.signal = "Buy"
    run.final_report = "# Trading Analysis Report\n\nUpdated share."

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run if run_id == "share-run" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post("/api/runs/share-run/public-share", headers={"X-TradingAgents-Tenant": "tenant-a"})

    assert response.status_code == 201
    payload = response.json()
    assert payload["share_id"] == "share-abc123"
    assert len(state["public_run_shares"]["items"]) == 1
    assert state["public_run_shares"]["items"][0]["final_report"] == "# Trading Analysis Report\n\nUpdated share."
    assert state["public_run_shares"]["items"][0]["view_count"] == 3
    assert state["public_run_shares"]["items"][0]["last_viewed_at"] == "2026-01-15T11:00:00"
    assert state["public_run_shares"]["items"][0]["expires_at"] == "2026-01-20T10:00:00"
    assert state["public_run_shares"]["items"][0]["share_title"] == "NVDA Snapshot"
    assert state["public_run_shares"]["items"][0]["share_summary"] == "External summary"


def test_public_run_share_delete_removes_snapshot(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "public_run_shares": {
            "items": [
                {
                    "share_id": "share-abc123",
                    "tenant_id": "tenant-a",
                    "run_id": "share-run",
                    "ticker": "NVDA",
                    "date": "2026-01-15",
                    "asset_type": "stock",
                    "status": "completed",
                    "created_at": "2026-01-15T10:00:00",
                    "signal": "Buy",
                    "error": None,
                    "config_summary": {},
                    "report_sections": {"final_trade_decision": "Rating: Buy"},
                    "current_report": None,
                    "final_report": "# Trading Analysis Report\n\nOld share.",
                    "view_count": 1,
                    "last_viewed_at": "2026-01-15T11:00:00",
                    "expires_at": None,
                    "annotation": None,
                    "review": None,
                }
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.delete("/api/runs/share-run/public-share", headers={"X-TradingAgents-Tenant": "tenant-a"})

    assert response.status_code == 200
    assert response.json() == {"deleted": 1}
    assert state["public_run_shares"]["items"] == []


def test_public_run_share_page_renders_without_api_auth(monkeypatch, tmp_path):
    client = TestClient(app)
    default_settings = {
        "public_run_shares": {
            "items": [
                {
                    "share_id": "share-public",
                    "tenant_id": None,
                    "run_id": "share-run",
                    "ticker": "NVDA",
                    "date": "2026-01-15",
                    "asset_type": "stock",
                    "status": "completed",
                    "created_at": "2026-01-15T10:00:00",
                    "signal": "Buy",
                    "error": None,
                    "config_summary": {"provider": "openai"},
                    "report_sections": {"final_trade_decision": "Rating: Buy", "news_report": "Strong news tailwinds."},
                    "current_report": None,
                    "final_report": "# Trading Analysis Report\n\nBull case is stronger than bear case.",
                    "view_count": 0,
                    "last_viewed_at": None,
                    "expires_at": None,
                    "share_title": "NVDA Earnings Snapshot",
                    "share_summary": "A concise external share view.",
                    "annotation": None,
                    "review": None,
                }
            ]
        }
    }

    def _load(path=None):
        if path == tmp_path / "default.json":
            return default_settings
        return {}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    def _save(settings, path=None):
        if path == tmp_path / "default.json":
            default_settings.clear()
            default_settings.update(settings)

    monkeypatch.setattr(web_routes, "load_settings", _load)
    monkeypatch.setattr(web_routes, "save_settings", _save)
    monkeypatch.setattr(web_routes, "list_web_tenant_ids", lambda: [])

    response = client.get("/shared/share-public")

    assert response.status_code == 200
    assert "NVDA" in response.text
    assert "NVDA Earnings Snapshot" in response.text
    assert "A concise external share view." in response.text
    assert "Bull case is stronger than bear case." in response.text
    assert "Strong news tailwinds." in response.text
    assert default_settings["public_run_shares"]["items"][0]["view_count"] == 1
    assert default_settings["public_run_shares"]["items"][0]["last_viewed_at"]


def test_public_run_share_page_404s_when_expired(monkeypatch, tmp_path):
    client = TestClient(app)
    default_settings = {
        "public_run_shares": {
            "items": [
                {
                    "share_id": "share-expired",
                    "tenant_id": None,
                    "run_id": "share-run",
                    "ticker": "NVDA",
                    "date": "2026-01-15",
                    "asset_type": "stock",
                    "status": "completed",
                    "created_at": "2026-01-15T10:00:00",
                    "signal": "Buy",
                    "error": None,
                    "config_summary": {},
                    "report_sections": {},
                    "current_report": None,
                    "final_report": "Report",
                    "view_count": 2,
                    "last_viewed_at": "2026-01-15T12:00:00",
                    "expires_at": "2000-01-01T00:00:00",
                    "annotation": None,
                    "review": None,
                }
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: default_settings if path == tmp_path / "default.json" else {})
    monkeypatch.setattr(web_routes, "list_web_tenant_ids", lambda: [])

    response = client.get("/shared/share-expired")

    assert response.status_code == 404
    assert response.json()["detail"] == "Shared run not found"


def test_list_public_run_shares_returns_tenant_scoped_summaries(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "public_run_shares": {
            "items": [
                {
                    "share_id": "share-abc123",
                    "tenant_id": "tenant-a",
                    "run_id": "run-a",
                    "ticker": "NVDA",
                    "date": "2026-01-15",
                    "asset_type": "stock",
                    "status": "completed",
                    "created_at": "2026-01-15T10:00:00",
                    "signal": "Buy",
                    "error": None,
                    "config_summary": {"provider": "openai"},
                    "report_sections": {"final_trade_decision": "Rating: Buy"},
                    "current_report": None,
                    "final_report": "# Trading Analysis Report\n\nShared report.",
                    "view_count": 4,
                    "last_viewed_at": "2026-01-15T11:30:00",
                    "expires_at": "2026-01-20T10:00:00",
                    "share_title": "NVDA Snapshot",
                    "share_summary": "External summary",
                    "annotation": None,
                    "review": None,
                }
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    response = client.get("/api/public-shares", headers={"X-TradingAgents-Tenant": "tenant-a"})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["share_id"] == "share-abc123"
    assert payload[0]["url"] == "/shared/share-abc123"
    assert payload[0]["ticker"] == "NVDA"
    assert payload[0]["run_id"] == "run-a"
    assert payload[0]["view_count"] == 4
    assert payload[0]["last_viewed_at"] == "2026-01-15T11:30:00"
    assert payload[0]["expires_at"] == "2026-01-20T10:00:00"
    assert payload[0]["share_title"] == "NVDA Snapshot"
    assert payload[0]["share_summary"] == "External summary"


def test_list_public_run_shares_can_filter_by_query_and_availability(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "public_run_shares": {
            "items": [
                {
                    "share_id": "share-active",
                    "tenant_id": "tenant-a",
                    "run_id": "run-a",
                    "ticker": "NVDA",
                    "date": "2026-01-15",
                    "asset_type": "stock",
                    "status": "completed",
                    "created_at": "2026-01-15T10:00:00",
                    "signal": "Buy",
                    "view_count": 1,
                    "last_viewed_at": None,
                    "expires_at": None,
                    "share_title": "NVDA Snapshot",
                    "share_summary": "Growth setup",
                    "config_summary": {},
                    "report_sections": {},
                    "current_report": None,
                    "final_report": "Report",
                    "annotation": None,
                    "review": None,
                },
                {
                    "share_id": "share-expired",
                    "tenant_id": "tenant-a",
                    "run_id": "run-b",
                    "ticker": "AAPL",
                    "date": "2026-01-16",
                    "asset_type": "stock",
                    "status": "completed",
                    "created_at": "2026-01-16T10:00:00",
                    "signal": "Hold",
                    "view_count": 0,
                    "last_viewed_at": None,
                    "expires_at": "2000-01-01T00:00:00",
                    "share_title": "AAPL Snapshot",
                    "share_summary": "Expired",
                    "config_summary": {},
                    "report_sections": {},
                    "current_report": None,
                    "final_report": "Report",
                    "annotation": None,
                    "review": None,
                },
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    active = client.get("/api/public-shares", headers={"X-TradingAgents-Tenant": "tenant-a"}, params={"availability": "active"})
    expired = client.get("/api/public-shares", headers={"X-TradingAgents-Tenant": "tenant-a"}, params={"availability": "expired"})
    searched = client.get("/api/public-shares", headers={"X-TradingAgents-Tenant": "tenant-a"}, params={"q": "growth"})

    assert [item["share_id"] for item in active.json()] == ["share-active"]
    assert [item["share_id"] for item in expired.json()] == ["share-expired"]
    assert [item["share_id"] for item in searched.json()] == ["share-active"]


def test_public_run_shares_export_csv_respects_filters(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "public_run_shares": {
            "items": [
                {
                    "share_id": "share-active",
                    "tenant_id": "tenant-a",
                    "run_id": "run-a",
                    "ticker": "NVDA",
                    "date": "2026-01-15",
                    "asset_type": "stock",
                    "status": "completed",
                    "created_at": "2026-01-15T10:00:00",
                    "signal": "Buy",
                    "view_count": 1,
                    "last_viewed_at": None,
                    "expires_at": None,
                    "share_title": "NVDA Snapshot",
                    "share_summary": "Growth setup",
                    "config_summary": {},
                    "report_sections": {},
                    "current_report": None,
                    "final_report": "Report",
                    "annotation": None,
                    "review": None,
                },
                {
                    "share_id": "share-expired",
                    "tenant_id": "tenant-a",
                    "run_id": "run-b",
                    "ticker": "AAPL",
                    "date": "2026-01-16",
                    "asset_type": "stock",
                    "status": "completed",
                    "created_at": "2026-01-16T10:00:00",
                    "signal": "Hold",
                    "view_count": 0,
                    "last_viewed_at": None,
                    "expires_at": "2000-01-01T00:00:00",
                    "share_title": "AAPL Snapshot",
                    "share_summary": "Expired",
                    "config_summary": {},
                    "report_sections": {},
                    "current_report": None,
                    "final_report": "Report",
                    "annotation": None,
                    "review": None,
                },
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    response = client.get("/api/public-shares/export", headers={"X-TradingAgents-Tenant": "tenant-a"}, params={"availability": "active"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "tradingagents-public-shares-tenant-a-" in response.headers["content-disposition"]
    assert "share_id,url,created_at,run_id,ticker,date,status,signal,view_count,last_viewed_at,expires_at,share_title,share_summary" in response.text
    assert "share-active,/shared/share-active,2026-01-15T10:00:00,run-a,NVDA" in response.text
    assert "share-expired" not in response.text


def test_public_run_share_update_can_set_and_clear_expiry(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "public_run_shares": {
            "items": [
                {
                    "share_id": "share-abc123",
                    "tenant_id": "tenant-a",
                    "run_id": "share-run",
                    "ticker": "NVDA",
                    "date": "2026-01-15",
                    "asset_type": "stock",
                    "status": "completed",
                    "created_at": "2026-01-15T10:00:00",
                    "signal": "Buy",
                    "error": None,
                    "config_summary": {},
                    "report_sections": {},
                    "current_report": None,
                    "final_report": "Report",
                    "view_count": 0,
                    "last_viewed_at": None,
                    "expires_at": None,
                    "share_title": None,
                    "share_summary": None,
                    "annotation": None,
                    "review": None,
                }
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    set_expiry = client.patch("/api/runs/share-run/public-share", headers={"X-TradingAgents-Tenant": "tenant-a"}, json={"expires_in_days": 7})
    clear_expiry = client.patch("/api/runs/share-run/public-share", headers={"X-TradingAgents-Tenant": "tenant-a"}, json={"expires_in_days": None})

    assert set_expiry.status_code == 200
    assert set_expiry.json()["expires_at"] is not None
    assert state["public_run_shares"]["items"][0]["expires_at"] is None
    assert clear_expiry.status_code == 200
    assert clear_expiry.json()["expires_at"] is None


def test_public_run_share_update_can_set_title_and_summary(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "public_run_shares": {
            "items": [
                {
                    "share_id": "share-abc123",
                    "tenant_id": "tenant-a",
                    "run_id": "share-run",
                    "ticker": "NVDA",
                    "date": "2026-01-15",
                    "asset_type": "stock",
                    "status": "completed",
                    "created_at": "2026-01-15T10:00:00",
                    "signal": "Buy",
                    "error": None,
                    "config_summary": {},
                    "report_sections": {},
                    "current_report": None,
                    "final_report": "Report",
                    "view_count": 0,
                    "last_viewed_at": None,
                    "expires_at": None,
                    "share_title": None,
                    "share_summary": None,
                    "annotation": None,
                    "review": None,
                }
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / f"{tenant_id or 'default'}.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.patch(
        "/api/runs/share-run/public-share",
        headers={"X-TradingAgents-Tenant": "tenant-a"},
        json={"share_title": "NVDA Snapshot", "share_summary": "External summary"},
    )

    assert response.status_code == 200
    assert response.json()["share_title"] == "NVDA Snapshot"
    assert response.json()["share_summary"] == "External summary"


def test_workspace_search_returns_cross_entity_matches(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"id": "watch-a", "ticker": "NVDA", "created_at": "2026-01-10T09:00:00"}]},
        "alerts": {"rules": [{"id": "alert-a", "ticker": "NVDA", "field": "signal", "value": "Buy", "created_at": "2026-01-11T09:00:00"}]},
        "portfolio": {"positions": [{"id": "pos-a", "ticker": "NVDA", "quantity": 10, "average_cost": 100.0, "created_at": "2026-01-12T09:00:00"}]},
        "presets": {"items": [{"id": "preset-a", "name": "NVDA Momentum", "created_at": "2026-01-13T09:00:00", "analysis_request": {"ticker": "NVDA", "llm_provider": "openai"}}]},
        "notes": {"items": [{"id": "note-a", "content": "Need to revisit NVDA after earnings.", "tags": ["earnings"], "ticker": "NVDA", "run_id": None, "created_at": "2026-01-14T09:00:00", "updated_at": "2026-01-14T09:00:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run = _make_run("run-a")
    run.ticker = "NVDA"
    run.signal = "Buy"
    run.status = "completed"
    run.date = "2026-01-15"
    run.created_at = "2026-01-15T09:00:00"
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/search", params={"q": "nvda"})

    assert response.status_code == 200
    payload = response.json()
    kinds = [item["kind"] for item in payload["results"]]
    assert "run" in kinds
    assert "note" in kinds
    assert "watchlist" in kinds
    assert "portfolio" in kinds
    assert "preset" in kinds
    assert "alert" in kinds


def test_workspace_search_can_return_search_view_member_and_share_kinds(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "saved_searches": {"items": [{"id": "search-a", "name": "Alpha Search", "query": "alpha thesis", "kinds": ["run"], "created_at": "2026-01-10T09:00:00"}]},
        "saved_views": {"items": [{"id": "view-a", "name": "Alpha View", "url": "/?view=briefing", "visible_panels": ["dashboard-panel"], "created_at": "2026-01-10T10:00:00"}]},
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "role": "analyst", "created_at": "2026-01-10T11:00:00"}]},
        "public_run_shares": {"items": [{"share_id": "share-a", "tenant_id": None, "run_id": "run-a", "ticker": "ALPHA", "date": "2026-01-15", "asset_type": "stock", "status": "completed", "created_at": "2026-01-10T12:00:00", "signal": "Buy", "view_count": 0, "last_viewed_at": None, "expires_at": None, "config_summary": {}, "report_sections": {}, "current_report": None, "final_report": "Report", "annotation": None, "review": None}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    response = client.get("/api/search", params={"q": "alpha", "kinds": "search,view,member,share"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_kinds"] == ["search", "view", "member", "share"]
    assert [item["kind"] for item in payload["results"]] == ["search", "view", "member", "share"]


def test_workspace_search_can_filter_by_kind(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"id": "watch-a", "ticker": "NVDA", "created_at": "2026-01-10T09:00:00"}]},
        "notes": {"items": [{"id": "note-a", "content": "Need to revisit NVDA after earnings.", "tags": ["earnings"], "ticker": "NVDA", "run_id": None, "created_at": "2026-01-14T09:00:00", "updated_at": "2026-01-14T09:00:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    response = client.get("/api/search", params={"q": "nvda", "kinds": "note"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_kinds"] == ["note"]
    assert [item["kind"] for item in payload["results"]] == ["note"]


def test_workspace_search_export_csv_returns_filtered_matches(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "watchlist": {"tickers": [{"id": "watch-a", "ticker": "NVDA", "created_at": "2026-01-10T09:00:00"}]},
        "notes": {"items": [{"id": "note-a", "content": "Need to revisit NVDA after earnings.", "tags": ["earnings"], "ticker": "NVDA", "run_id": None, "created_at": "2026-01-14T09:00:00", "updated_at": "2026-01-14T09:00:00"}]},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    response = client.get("/api/search/export", params={"q": "nvda", "kinds": "note"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "tradingagents-workspace-search-default-" in response.headers["content-disposition"]
    assert "kind,entity_id,title,subtitle,excerpt,ticker,run_id" in response.text
    assert "note,note-a,NVDA,2026-01-14T09:00:00,Need to revisit NVDA after earnings.,NVDA," in response.text
    assert "watchlist" not in response.text


def test_saved_search_endpoints_round_trip(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-10T08:00:00"}]},
        "saved_searches": {"items": []},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    create = client.post(
        "/api/searches",
        json={
            "name": "Risk Notes",
            "query": "risk",
            "kinds": ["note", "alert"],
            "group": "Collaboration",
            "pinned": True,
            "archived": False,
            "member_id": "member-a",
        },
    )
    listing = client.get("/api/searches")
    delete = client.delete(f"/api/searches/{create.json()['id']}")

    assert create.status_code == 201
    assert create.json()["kinds"] == ["note", "alert"]
    assert create.json()["group"] == "Collaboration"
    assert create.json()["pinned"] is True
    assert create.json()["member_id"] == "member-a"
    assert create.json()["member_name"] == "Alice"
    assert listing.status_code == 200
    assert listing.json()[0]["name"] == "Risk Notes"
    assert delete.status_code == 200
    assert delete.json() == {"deleted": 1}


def test_saved_search_update_can_toggle_pinned_and_group(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "saved_searches": {
            "items": [
                {"id": "search-a", "name": "Risk Notes", "query": "risk", "kinds": ["note"], "group": None, "pinned": False, "created_at": "2026-01-10T08:00:00"}
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.patch("/api/searches/search-a", json={"group": "Collaboration", "pinned": True})

    assert response.status_code == 200
    assert response.json()["group"] == "Collaboration"
    assert response.json()["pinned"] is True


def test_saved_search_update_can_rename(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "saved_searches": {
            "items": [
                {"id": "search-a", "name": "Risk Notes", "query": "risk", "kinds": ["note"], "group": None, "pinned": False, "created_at": "2026-01-10T08:00:00"}
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.patch("/api/searches/search-a", json={"name": "Risk Inbox"})

    assert response.status_code == 200
    assert response.json()["name"] == "Risk Inbox"


def test_saved_search_update_can_archive(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "saved_searches": {
            "items": [
                {"id": "search-a", "name": "Risk Notes", "query": "risk", "kinds": ["note"], "group": None, "pinned": False, "archived": False, "created_at": "2026-01-10T08:00:00"}
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.patch("/api/searches/search-a", json={"archived": True})

    assert response.status_code == 200
    assert response.json()["archived"] is True


def test_saved_search_duplicate_creates_copy(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "saved_searches": {
            "items": [
                {"id": "search-a", "name": "Risk Notes", "query": "risk", "kinds": ["note"], "group": "Collaboration", "pinned": True, "created_at": "2026-01-10T08:00:00"}
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post("/api/searches/search-a/duplicate")

    assert response.status_code == 201
    assert response.json()["name"] == "Risk Notes Copy"
    assert response.json()["query"] == "risk"
    assert len(state["saved_searches"]["items"]) == 2


def test_saved_view_endpoints_round_trip(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-10T08:00:00"}]},
        "saved_views": {"items": []},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    create = client.post(
        "/api/views",
        json={
            "name": "NVDA Compare",
            "url": "/?ticker=NVDA&compare_left_run_id=a&compare_right_run_id=b&panels=config-panel,history-panel",
            "visible_panels": ["config-panel", "history-panel"],
            "group": "Team Daily",
            "pinned": True,
            "archived": False,
            "member_id": "member-a",
        },
    )
    listing = client.get("/api/views")
    delete = client.delete(f"/api/views/{create.json()['id']}")

    assert create.status_code == 201
    assert create.json()["name"] == "NVDA Compare"
    assert create.json()["visible_panels"] == ["config-panel", "history-panel"]
    assert create.json()["group"] == "Team Daily"
    assert create.json()["pinned"] is True
    assert create.json()["member_id"] == "member-a"
    assert create.json()["member_name"] == "Alice"
    assert listing.status_code == 200
    assert listing.json()[0]["url"].startswith("/?ticker=NVDA")
    assert delete.status_code == 200
    assert delete.json() == {"deleted": 1}


def test_saved_view_update_can_toggle_pinned_and_group(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "saved_views": {
            "items": [
                {"id": "view-a", "name": "NVDA Compare", "url": "/?ticker=NVDA", "visible_panels": ["config-panel"], "group": None, "pinned": False, "created_at": "2026-01-10T08:00:00"}
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.patch("/api/views/view-a", json={"group": "Team Daily", "pinned": True})

    assert response.status_code == 200
    assert response.json()["group"] == "Team Daily"
    assert response.json()["pinned"] is True


def test_saved_view_update_can_rename(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "saved_views": {
            "items": [
                {"id": "view-a", "name": "NVDA Compare", "url": "/?ticker=NVDA", "visible_panels": ["config-panel"], "group": None, "pinned": False, "created_at": "2026-01-10T08:00:00"}
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.patch("/api/views/view-a", json={"name": "NVDA Morning View"})

    assert response.status_code == 200
    assert response.json()["name"] == "NVDA Morning View"


def test_saved_view_update_can_archive(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "saved_views": {
            "items": [
                {"id": "view-a", "name": "NVDA Compare", "url": "/?ticker=NVDA", "visible_panels": ["config-panel"], "group": None, "pinned": False, "archived": False, "created_at": "2026-01-10T08:00:00"}
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.patch("/api/views/view-a", json={"archived": True})

    assert response.status_code == 200
    assert response.json()["archived"] is True


def test_saved_view_duplicate_creates_copy(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "saved_views": {
            "items": [
                {"id": "view-a", "name": "NVDA Compare", "url": "/?ticker=NVDA", "visible_panels": ["config-panel"], "group": "Team Daily", "pinned": True, "created_at": "2026-01-10T08:00:00"}
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    response = client.post("/api/views/view-a/duplicate")

    assert response.status_code == 201
    assert response.json()["name"] == "NVDA Compare Copy"
    assert response.json()["url"] == "/?ticker=NVDA"
    assert len(state["saved_views"]["items"]) == 2


def test_pinned_runs_endpoint_returns_saved_items(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "pinned_runs": {
            "items": [
                {"run_id": "run-a", "note": "Core thesis", "category": "high-conviction", "priority": "p1", "next_action": "Review after earnings", "action_status": "todo", "assignee": "Alice", "created_at": "2026-01-10T09:00:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run = _make_run("run-a")
    run.ticker = "NVDA"
    run.signal = "Buy"
    run.status = "completed"
    run.date = "2026-01-15"
    run.created_at = "2026-01-15T09:00:00"
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run if run_id == "run-a" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/pinned-runs")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["run_id"] == "run-a"
    assert payload[0]["ticker"] == "NVDA"
    assert payload[0]["note"] == "Core thesis"
    assert payload[0]["category"] == "high-conviction"
    assert payload[0]["priority"] == "p1"
    assert payload[0]["next_action"] == "Review after earnings"
    assert payload[0]["action_status"] == "todo"
    assert payload[0]["assignee"] == "Alice"


def test_pinned_run_post_and_delete_round_trip(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "workspace_members": {"items": [{"id": "member-a", "name": "Alice", "created_at": "2026-01-10T08:00:00"}]},
        "pinned_runs": {"items": []},
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run = _make_run("run-a")
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run if run_id == "run-a" else None)
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    create = client.post("/api/pinned-runs", json={
        "run_id": "run-a",
        "note": "Watch closely",
        "category": "follow-up",
        "priority": "p2",
        "next_action": "Check guidance on Friday",
        "action_status": "todo",
        "assignee": "Alice",
        "due_date": "2026-01-20",
        "snoozed_until": "2026-01-18",
    })
    delete = client.delete("/api/pinned-runs/run-a")

    assert create.status_code == 201
    assert create.json()["note"] == "Watch closely"
    assert create.json()["category"] == "follow-up"
    assert create.json()["priority"] == "p2"
    assert create.json()["next_action"] == "Check guidance on Friday"
    assert create.json()["action_status"] == "todo"
    assert create.json()["assignee"] == "Alice"
    assert create.json()["due_date"] == "2026-01-20"
    assert create.json()["snoozed_until"] == "2026-01-18"
    assert delete.status_code == 200
    assert delete.json() == {"deleted": 1}


def test_pinned_runs_can_filter_by_category(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "pinned_runs": {
            "items": [
                {"run_id": "run-a", "note": "Core thesis", "category": "high-conviction", "priority": "p1", "created_at": "2026-01-10T09:00:00"},
                {"run_id": "run-b", "note": "Follow later", "category": "follow-up", "priority": "p3", "created_at": "2026-01-11T09:00:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run_a = _make_run("run-a")
    run_b = _make_run("run-b")
    monkeypatch.setattr(
        web_routes,
        "get_run",
        lambda run_id, tenant_id=None: {"run-a": run_a, "run-b": run_b}.get(run_id),
    )
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/pinned-runs", params={"category": "follow-up"})

    assert response.status_code == 200
    payload = response.json()
    assert [item["run_id"] for item in payload] == ["run-b"]


def test_pinned_runs_can_filter_by_action_status(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "pinned_runs": {
            "items": [
                {"run_id": "run-a", "note": "Core thesis", "category": "high-conviction", "priority": "p1", "next_action": "Review after earnings", "action_status": "todo", "created_at": "2026-01-10T09:00:00"},
                {"run_id": "run-b", "note": "Follow later", "category": "follow-up", "priority": "p3", "next_action": "Recheck sentiment", "action_status": "done", "created_at": "2026-01-11T09:00:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run_a = _make_run("run-a")
    run_b = _make_run("run-b")
    monkeypatch.setattr(
        web_routes,
        "get_run",
        lambda run_id, tenant_id=None: {"run-a": run_a, "run-b": run_b}.get(run_id),
    )
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/pinned-runs", params={"action_status": "todo"})

    assert response.status_code == 200
    payload = response.json()
    assert [item["run_id"] for item in payload] == ["run-a"]


def test_action_board_groups_pinned_runs_by_status(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "pinned_runs": {
            "items": [
                {"run_id": "run-a", "note": "Core thesis", "category": "high-conviction", "priority": "p1", "next_action": "Review after earnings", "action_status": "todo", "created_at": "2026-01-10T09:00:00"},
                {"run_id": "run-b", "note": "In progress", "category": "follow-up", "priority": "p2", "next_action": "Update model", "action_status": "doing", "created_at": "2026-01-11T09:00:00"},
                {"run_id": "run-c", "note": "Completed", "category": "archive", "priority": "p3", "next_action": "Log outcome", "action_status": "done", "created_at": "2026-01-12T09:00:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    runs = {
        "run-a": _make_run("run-a"),
        "run-b": _make_run("run-b"),
        "run-c": _make_run("run-c"),
    }
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: runs.get(run_id))
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    response = client.get("/api/action-board")

    assert response.status_code == 200
    payload = response.json()
    assert [item["run_id"] for item in payload["todo"]] == ["run-a"]
    assert [item["run_id"] for item in payload["doing"]] == ["run-b"]
    assert [item["run_id"] for item in payload["done"]] == ["run-c"]


def test_pinned_run_action_status_update(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {
        "pinned_runs": {
            "items": [
                {"run_id": "run-a", "note": "Core thesis", "category": "high-conviction", "priority": "p1", "next_action": "Review after earnings", "action_status": "todo", "created_at": "2026-01-10T09:00:00"},
            ]
        }
    }

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: _make_run("run-a"))

    response = client.patch("/api/pinned-runs/run-a/status", json={"action_status": "doing"})

    assert response.status_code == 200
    assert response.json()["action_status"] == "doing"


def test_run_annotation_round_trip_and_run_views_include_annotation(monkeypatch, tmp_path):
    client = TestClient(app)
    state = {"run_annotations": {"items": []}}

    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: tmp_path / "tenant.json")
    monkeypatch.setattr(web_routes, "load_settings", lambda path=None: state)

    run = _make_run("run-a")
    run.ticker = "NVDA"
    run.signal = "Buy"
    run.status = "completed"
    run.date = "2026-01-15"
    run.created_at = "2026-01-15T09:00:00"
    monkeypatch.setattr(web_routes, "get_run", lambda run_id, tenant_id=None: run if run_id == "run-a" else None)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run])
    monkeypatch.setattr(web_routes, "get_queue_position", lambda run_id, tenant_id=None: None)

    def _save(settings, path=None):
        state.clear()
        state.update(settings)

    monkeypatch.setattr(web_routes, "save_settings", _save)

    create = client.post(
        "/api/runs/run-a/annotation",
        json={"label": "High Conviction", "summary": "Best setup this week.", "next_step": "Review after earnings"},
    )
    status_resp = client.get("/api/runs/run-a")
    list_resp = client.get("/api/runs")
    delete = client.delete("/api/runs/run-a/annotation")

    assert create.status_code == 201
    assert create.json()["label"] == "High Conviction"
    assert status_resp.status_code == 200
    assert status_resp.json()["annotation"]["label"] == "High Conviction"
    assert list_resp.status_code == 200
    assert list_resp.json()[0]["annotation"]["next_step"] == "Review after earnings"
    assert delete.status_code == 200
    assert delete.json() == {"deleted": 1}


def test_list_runs_uses_request_tenant_header(monkeypatch):
    client = TestClient(app)
    seen: dict[str, str | None] = {}

    def _list_runs(tenant_id=None):
        seen["tenant_id"] = tenant_id
        return []

    monkeypatch.setattr(web_routes, "list_runs", _list_runs)

    response = client.get("/api/runs", headers={"X-TradingAgents-Tenant": "tenant-a"})

    assert response.status_code == 200
    assert seen["tenant_id"] == "tenant-a"


def test_list_runs_uses_request_tenant_query(monkeypatch):
    client = TestClient(app)
    seen: dict[str, str | None] = {}

    def _list_runs(tenant_id=None):
        seen["tenant_id"] = tenant_id
        return []

    monkeypatch.setattr(web_routes, "list_runs", _list_runs)

    response = client.get("/api/runs?tenant_id=tenant-q")

    assert response.status_code == 200
    assert seen["tenant_id"] == "tenant-q"


def test_cancel_run_endpoint_returns_run_payload(monkeypatch):
    client = TestClient(app)
    run = _make_run()
    run.status = "cancelling"

    monkeypatch.setattr(web_routes, "cancel_run", lambda _run_id, tenant_id=None: run)

    response = client.post(f"/api/runs/{run.run_id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelling"


def test_get_run_timeline_returns_persisted_events(monkeypatch):
    client = TestClient(app)
    run = _make_run()
    run.event_history = [
        {
            "timestamp": "2026-01-15T00:00:00",
            "event": "progress",
            "data": {"message": "hello"},
        }
    ]

    monkeypatch.setattr(web_routes, "get_run", lambda _run_id, tenant_id=None: run)

    response = client.get(f"/api/runs/{run.run_id}/timeline")

    assert response.status_code == 200
    assert response.json()[0]["event"] == "progress"
    assert response.json()[0]["data"]["message"] == "hello"


def test_stream_run_events_reads_persisted_history_in_external_worker_mode(monkeypatch):
    client = TestClient(app)
    run = _make_run()
    run.status = "completed"
    run.event_history = [
        {
            "timestamp": "2026-01-15T00:00:00",
            "event": "progress",
            "data": {"message": "hello"},
        },
        {
            "timestamp": "2026-01-15T00:01:00",
            "event": "complete",
            "data": {"signal": "Buy", "report": ""},
        },
    ]

    monkeypatch.setattr(web_routes, "get_execution_mode", lambda: "external_worker")
    monkeypatch.setattr(web_routes, "get_run", lambda _run_id, tenant_id=None: run)

    with client.stream("GET", f"/api/runs/{run.run_id}/events") as response:
        body = "".join(chunk.decode("utf-8") for chunk in response.iter_raw())

    assert response.status_code == 200
    assert "event: progress" in body
    assert "hello" in body
    assert "event: complete" in body


def test_get_run_status_includes_config_summary(monkeypatch):
    client = TestClient(app)
    run = _make_run()
    run.config.update({
        "llm_provider": "openai",
        "quick_think_llm": "gpt-5.4-mini",
        "deep_think_llm": "gpt-5.5",
        "output_language": "Chinese",
        "market_profile": "cn_a",
        "max_debate_rounds": 3,
        "max_risk_discuss_rounds": 2,
        "checkpoint_enabled": True,
        "benchmark_ticker": "QQQ",
        "memory_log_max_entries": 25,
        "data_vendors": {"news_data": "cn_news"},
        "tool_vendors": {"get_global_news": "alpha_vantage"},
        "global_news_queries": ["asia earnings outlook"],
    })
    run.selected_analysts = ["market", "news"]
    monkeypatch.setattr(web_routes, "get_run", lambda _run_id, tenant_id=None: run)

    response = client.get(f"/api/runs/{run.run_id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["config_summary"]["llm_provider"] == "openai"
    assert payload["config_summary"]["output_language"] == "Chinese"
    assert payload["config_summary"]["market_profile"] == "cn_a"
    assert payload["config_summary"]["selected_analysts"] == ["market", "news"]
    assert payload["config_summary"]["data_vendors"]["news_data"] == "cn_news"
    assert payload["config_summary"]["max_risk_discuss_rounds"] == 2
    assert payload["config_summary"]["benchmark_ticker"] == "QQQ"
    assert payload["config_summary"]["memory_log_max_entries"] == 25
    assert payload["config_summary"]["tool_vendors"]["get_global_news"] == "alpha_vantage"
    assert payload["config_summary"]["global_news_queries"] == ["asia earnings outlook"]


def test_list_run_artifacts_returns_available_downloads(monkeypatch, tmp_path):
    client = TestClient(app)
    run = _make_run()

    report_path = tmp_path / "complete_report.md"
    report_path.write_text("# Report\n", encoding="utf-8")
    section_path = tmp_path / "1_analysts" / "market.md"
    section_path.parent.mkdir()
    section_path.write_text("market", encoding="utf-8")
    state_path = tmp_path / "full_state.json"
    state_path.write_text('{"signal": "Buy"}', encoding="utf-8")

    run.report_path = str(report_path)
    run.state_log_path = str(state_path)
    monkeypatch.setattr(web_routes, "get_run", lambda _run_id, tenant_id=None: run)

    response = client.get(f"/api/runs/{run.run_id}/artifacts")

    assert response.status_code == 200
    assert response.json() == [
        {
            "name": "complete-report",
            "label": "Complete report",
            "download_url": f"/api/runs/{run.run_id}/artifacts/download?name=complete-report",
        },
        {
            "name": "full-state",
            "label": "Full state JSON",
            "download_url": f"/api/runs/{run.run_id}/artifacts/download?name=full-state",
        },
        {
            "name": "report-tree/1_analysts/market.md",
            "label": "1_analysts/market.md",
            "download_url": f"/api/runs/{run.run_id}/artifacts/download?name=report-tree/1_analysts/market.md",
        },
    ]


def test_artifact_library_returns_runs_with_download_links(monkeypatch):
    client = TestClient(app)
    run = _make_run("artifact-run")
    run.ticker = "NVDA"
    run.status = "completed"
    run.signal = "Buy"
    run.created_at = "2026-01-15T10:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [run])
    monkeypatch.setattr(
        web_routes,
        "build_run_artifacts",
        lambda report_path=None, state_log_path=None: [
            type("Artifact", (), {"key": "complete-report", "label": "Complete report", "path": None})(),
            type("Artifact", (), {"key": "full-state", "label": "Full state JSON", "path": None})(),
            type("Artifact", (), {"key": "report-tree/1_analysts/market.md", "label": "market.md", "path": None})(),
        ],
    )

    response = client.get("/api/artifacts/library")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["run_id"] == "artifact-run"
    assert payload[0]["artifact_count"] == 3
    assert payload[0]["report_download_url"] == f"/api/runs/{run.run_id}/artifacts/download?name=complete-report"
    assert payload[0]["state_download_url"] == f"/api/runs/{run.run_id}/artifacts/download?name=full-state"


def test_artifact_library_export_csv_returns_filtered_rows(monkeypatch):
    client = TestClient(app)
    nvda = _make_run("artifact-run")
    nvda.ticker = "NVDA"
    nvda.status = "completed"
    nvda.signal = "Buy"
    nvda.created_at = "2026-01-15T10:00:00"

    aapl = _make_run("other-run")
    aapl.ticker = "AAPL"
    aapl.status = "completed"
    aapl.signal = "Hold"
    aapl.created_at = "2026-01-15T09:00:00"

    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [nvda, aapl])
    monkeypatch.setattr(
        web_routes,
        "build_run_artifacts",
        lambda report_path=None, state_log_path=None: [
            type("Artifact", (), {"key": "complete-report", "label": "Complete report", "path": None})(),
        ],
    )

    response = client.get("/api/artifacts/library/export", params={"q": "nvda"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert "tradingagents-artifact-library-default-" in response.headers["content-disposition"]
    assert "run_id,ticker,date,status,created_at,signal,error,artifact_count,report_download_url,state_download_url" in response.text
    assert "artifact-run,NVDA,2026-01-15,completed,2026-01-15T10:00:00,Buy," in response.text
    assert "other-run" not in response.text


def test_download_run_report_returns_saved_markdown(monkeypatch, tmp_path):
    client = TestClient(app)
    run = _make_run()

    report_path = tmp_path / "complete_report.md"
    report_path.write_text("# Report\ncontent", encoding="utf-8")
    run.report_path = str(report_path)
    monkeypatch.setattr(web_routes, "get_run", lambda _run_id, tenant_id=None: run)

    response = client.get(f"/api/runs/{run.run_id}/report")

    assert response.status_code == 200
    assert response.text == "# Report\ncontent"


def test_download_named_run_artifact_returns_report_tree_file(monkeypatch, tmp_path):
    client = TestClient(app)
    run = _make_run()

    report_root = tmp_path / "reports"
    report_root.mkdir()
    complete = report_root / "complete_report.md"
    complete.write_text("# Report\n", encoding="utf-8")
    market = report_root / "1_analysts" / "market.md"
    market.parent.mkdir()
    market.write_text("market", encoding="utf-8")
    run.report_path = str(complete)
    monkeypatch.setattr(web_routes, "get_run", lambda _run_id, tenant_id=None: run)

    response = client.get(
        f"/api/runs/{run.run_id}/artifacts/download",
        params={"name": "report-tree/1_analysts/market.md"},
    )

    assert response.status_code == 200
    assert response.text == "market"


def test_get_named_run_artifact_content_returns_text(monkeypatch, tmp_path):
    client = TestClient(app)
    run = _make_run()

    report_root = tmp_path / "reports"
    report_root.mkdir()
    complete = report_root / "complete_report.md"
    complete.write_text("# Report\n", encoding="utf-8")
    market = report_root / "1_analysts" / "market.md"
    market.parent.mkdir()
    market.write_text("market", encoding="utf-8")
    run.report_path = str(complete)
    monkeypatch.setattr(web_routes, "get_run", lambda _run_id, tenant_id=None: run)

    response = client.get(
        f"/api/runs/{run.run_id}/artifacts/content",
        params={"name": "report-tree/1_analysts/market.md"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["name"] == "report-tree/1_analysts/market.md"
    assert payload["content"] == "market"


def test_download_run_full_state_404s_when_missing(monkeypatch):
    client = TestClient(app)
    run = _make_run()
    monkeypatch.setattr(web_routes, "get_run", lambda _run_id, tenant_id=None: run)

    response = client.get(f"/api/runs/{run.run_id}/artifacts/full-state")

    assert response.status_code == 404
    assert response.json()["detail"] == "Full state log not available"


def test_cancel_run_endpoint_404s_for_unknown_run(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(web_routes, "cancel_run", lambda _run_id, tenant_id=None: None)

    response = client.post("/api/runs/missing/cancel")

    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found"


def test_delete_run_endpoint_returns_204(monkeypatch):
    client = TestClient(app)
    run = _make_run()
    monkeypatch.setattr(web_routes, "delete_run", lambda _run_id, tenant_id=None: run)

    response = client.delete(f"/api/runs/{run.run_id}")

    assert response.status_code == 204


def test_delete_run_endpoint_409s_for_active_run(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(web_routes, "delete_run", lambda _run_id, tenant_id=None: None)
    active_run = _make_run("active")
    active_run.status = "running"
    monkeypatch.setattr(web_routes, "get_run", lambda _run_id, tenant_id=None: active_run)

    response = client.delete(f"/api/runs/{active_run.run_id}")

    assert response.status_code == 409
    assert response.json()["detail"] == "Run is still active"


def test_retry_run_endpoint_returns_new_run(monkeypatch):
    client = TestClient(app)
    run = _make_run("retried")
    run.status = "queued"
    monkeypatch.setattr(web_routes, "retry_run", lambda _run_id, tenant_id=None: run)

    response = client.post("/api/runs/source/retry")

    assert response.status_code == 201
    assert response.json()["run_id"] == "retried"
    assert response.json()["status"] == "queued"


def test_retry_run_endpoint_409s_for_active_source(monkeypatch):
    client = TestClient(app)
    active_run = _make_run("active")
    active_run.status = "running"
    monkeypatch.setattr(web_routes, "retry_run", lambda _run_id, tenant_id=None: None)
    monkeypatch.setattr(web_routes, "get_run", lambda _run_id, tenant_id=None: active_run)

    response = client.post("/api/runs/active/retry")

    assert response.status_code == 409
    assert response.json()["detail"] == "Run is still active"


def test_get_system_status_reports_execution_mode(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(web_routes, "get_execution_mode", lambda: "external_worker")
    monkeypatch.setattr(web_routes, "get_tenant_id", lambda tenant_id=None: tenant_id or "tenant-a")
    monkeypatch.setattr(web_routes, "get_state_backend", lambda: "sqlite")
    monkeypatch.setattr(web_routes, "get_state_location", lambda tenant_id=None: "/shared/web/state.db")
    monkeypatch.setattr(web_routes, "get_auth_scope", lambda tenant_id=None: "tenant")
    monkeypatch.setattr(
        web_routes,
        "get_service_status",
        lambda tenant_id=None: {
            "queue_depth": 2,
            "run_count": 5,
            "worker_running": False,
            "worker_mode": "external_worker",
            "worker_last_seen": "2026-06-29T01:00:00",
        },
    )

    response = client.get("/api/system/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["execution_mode"] == "external_worker"
    assert payload["tenant_id"] == "tenant-a"
    assert payload["state_backend"] == "sqlite"
    assert payload["state_location"] == "/shared/web/state.db"
    assert payload["auth_scope"] == "tenant"
    assert payload["queue_depth"] == 2
    assert payload["run_count"] == 5
    assert payload["worker_running"] is False
    assert payload["worker_mode"] == "external_worker"
    assert payload["worker_last_seen"] == "2026-06-29T01:00:00"


def test_get_system_status_uses_request_tenant_header(monkeypatch):
    client = TestClient(app)
    seen: dict[str, str | None] = {}

    monkeypatch.setattr(web_routes, "get_execution_mode", lambda: "external_worker")
    monkeypatch.setattr(web_routes, "get_tenant_id", lambda tenant_id=None: tenant_id or "default")
    monkeypatch.setattr(web_routes, "get_state_backend", lambda tenant_id=None: "sqlite")
    monkeypatch.setattr(web_routes, "get_state_location", lambda tenant_id=None: f"/state/{tenant_id}")

    def _status(tenant_id=None):
        seen["tenant_id"] = tenant_id
        return {"queue_depth": 0, "run_count": 0, "worker_running": False, "worker_mode": None, "worker_last_seen": None}

    monkeypatch.setattr(web_routes, "get_service_status", _status)

    response = client.get("/api/system/status", headers={"X-TradingAgents-Tenant": "tenant-a"})

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-a"
    assert response.json()["state_location"] == "/state/tenant-a"
    assert seen["tenant_id"] == "tenant-a"


def test_get_system_status_uses_request_tenant_query(monkeypatch):
    client = TestClient(app)
    seen: dict[str, str | None] = {}

    monkeypatch.setattr(web_routes, "get_execution_mode", lambda: "external_worker")
    monkeypatch.setattr(web_routes, "get_tenant_id", lambda tenant_id=None: tenant_id or "default")
    monkeypatch.setattr(web_routes, "get_state_backend", lambda: "sqlite")
    monkeypatch.setattr(web_routes, "get_state_location", lambda tenant_id=None: f"/state/{tenant_id}")

    def _status(tenant_id=None):
        seen["tenant_id"] = tenant_id
        return {"queue_depth": 0, "run_count": 0, "worker_running": False, "worker_mode": None, "worker_last_seen": None}

    monkeypatch.setattr(web_routes, "get_service_status", _status)

    response = client.get("/api/system/status?tenant_id=tenant-q")

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "tenant-q"
    assert response.json()["state_location"] == "/state/tenant-q"
    assert seen["tenant_id"] == "tenant-q"
