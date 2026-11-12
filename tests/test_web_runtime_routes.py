"""Tests for runtime-maintenance web endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient

from web import routes as web_routes
from web.app import app
from web.user_store import UserStore


def _ensure_tenant_registry(monkeypatch, tmp_path, tenant_id: str) -> UserStore:
    db_path = tmp_path / "auth.db"
    monkeypatch.setenv("TRADINGAGENTS_WEB_AUTH_DB", str(db_path))
    store = UserStore(db_path)
    if store.get_tenant(tenant_id) is None:
        store.create_tenant(tenant_id, display_name=tenant_id)
    return store


def test_list_tenants_endpoint_marks_active_tenant(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(web_routes, "list_web_tenant_ids", lambda: ["tenant-a", "tenant-b"])
    monkeypatch.setattr(web_routes, "get_auth_scope", lambda tenant_id=None: "tenant")

    response = client.get("/api/system/tenants", headers={"X-TradingAgents-Tenant": "tenant-b"})

    assert response.status_code == 200
    assert response.json() == [
        {"tenant_id": None, "label": "default", "active": False},
        {"tenant_id": "tenant-a", "label": "tenant-a", "active": False},
        {"tenant_id": "tenant-b", "label": "tenant-b", "active": True},
    ]


def test_list_runtime_checkpoints_endpoint_returns_entries(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(
        web_routes,
        "list_runtime_checkpoints",
        lambda state_root: [
            {"run_id": None, "ticker": "NVDA", "path": "/tmp/cache/checkpoints/NVDA.db", "size_bytes": 123}
        ],
    )
    monkeypatch.setattr(web_routes, "get_web_state_dir", lambda tenant_id=None: "/tmp")

    response = client.get("/api/system/checkpoints")

    assert response.status_code == 200
    assert response.json() == [
        {"run_id": None, "ticker": "NVDA", "path": "/tmp/cache/checkpoints/NVDA.db", "size_bytes": 123}
    ]


def test_delete_runtime_checkpoints_endpoint_returns_deleted_count(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(web_routes, "clear_runtime_checkpoints", lambda state_root, ticker=None: 2)
    monkeypatch.setattr(web_routes, "get_web_state_dir", lambda tenant_id=None: "/tmp")

    response = client.delete("/api/system/checkpoints", params={"ticker": "NVDA"})

    assert response.status_code == 200
    assert response.json() == {"deleted": 2}


def test_list_runtime_memory_endpoint_returns_entries(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(
        web_routes,
        "list_runtime_memory_entries",
        lambda state_root: [
            {
                "run_id": None,
                "date": "2026-01-10",
                "ticker": "NVDA",
                "rating": "Buy",
                "pending": True,
                "raw": None,
                "alpha": None,
                "holding": None,
                "decision": "Rating: Buy",
                "reflection": "",
            }
        ],
    )
    monkeypatch.setattr(web_routes, "get_web_state_dir", lambda tenant_id=None: "/tmp")

    response = client.get("/api/system/memory")

    assert response.status_code == 200
    assert response.json()[0]["ticker"] == "NVDA"
    assert response.json()[0]["pending"] is True


def test_delete_runtime_memory_endpoint_returns_deleted_count(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(web_routes, "clear_runtime_memory_logs", lambda state_root: 1)
    monkeypatch.setattr(web_routes, "get_web_state_dir", lambda tenant_id=None: "/tmp")

    response = client.delete("/api/system/memory")

    assert response.status_code == 200
    assert response.json() == {"deleted": 1}


def test_migrate_all_settings_timestamps_endpoint_returns_updated_count(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(web_routes, "migrate_all_web_settings_timestamps_to_ms", lambda: 2)

    response = client.post("/api/system/settings/migrate-timestamps")

    assert response.status_code == 200
    assert response.json() == {"updated": 2}


def test_migrate_tenant_settings_timestamps_endpoint_targets_current_tenant(monkeypatch, tmp_path):
    client = TestClient(app)
    _ensure_tenant_registry(monkeypatch, tmp_path, "tenant-a")

    seen: dict[str, object] = {}
    monkeypatch.setattr(web_routes, "get_auth_scope", lambda tenant_id=None: "tenant")
    monkeypatch.setattr(web_routes, "get_web_settings_path", lambda tenant_id=None: f"/tmp/{tenant_id or 'default'}.json")

    def _migrate(path):
        seen["path"] = path
        return True

    monkeypatch.setattr(web_routes, "migrate_web_settings_timestamps_to_ms", _migrate)

    response = client.post(
        "/api/system/settings/migrate-timestamps",
        headers={"X-TradingAgents-Tenant": "tenant-a"},
    )

    assert response.status_code == 200
    assert response.json() == {"updated": 1}
    assert seen["path"] == "/tmp/tenant-a.json"


def test_list_tenants_endpoint_requires_tenant_scoped_auth_for_explicit_tenant(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(web_routes, "get_auth_scope", lambda tenant_id=None: "global")

    response = client.get("/api/system/tenants", headers={"X-TradingAgents-Tenant": "tenant-a"})

    assert response.status_code == 403


def test_runtime_maintenance_requires_tenant_scoped_auth_for_explicit_tenant(monkeypatch):
    client = TestClient(app)

    monkeypatch.setattr(web_routes, "get_auth_scope", lambda tenant_id=None: "disabled")

    response = client.get("/api/system/checkpoints", headers={"X-TradingAgents-Tenant": "tenant-a"})

    assert response.status_code == 403

    migrate_response = client.post("/api/system/settings/migrate-timestamps", headers={"X-TradingAgents-Tenant": "tenant-a"})

    assert migrate_response.status_code == 403
