"""Route-level tests for the FastAPI web layer."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.service.runtime_context import build_runtime_context
from web.app import app
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
            "analysis": {"market_profile": "cn_a", "checkpoint_enabled": True},
        },
    )

    assert response.status_code == 200
    assert captured["overwrite"] is True
    assert captured["saved"]["api_keys"]["openai"] == "sk-test"
    assert captured["exported"]["analysis"]["market_profile"] == "cn_a"


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
        "checkpoint_enabled": True,
        "data_vendors": {"news_data": "cn_news"},
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
