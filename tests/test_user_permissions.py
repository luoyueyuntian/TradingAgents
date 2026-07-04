from __future__ import annotations

from fastapi.testclient import TestClient

import web.auth_routes as auth_routes
import web.routes as web_routes
from web.app import app
from web.passwords import hash_password
from web.permissions import is_public_path
from web.user_store import UserStore


def _create_user(store: UserStore, **overrides):
    password_record = hash_password("StrongPass123!")
    values = {
        "username": "alice",
        "email": "alice@example.com",
        "display_name": "Alice Analyst",
        "role": "analyst",
        "tenant_id": "tenant-a",
        "password_hash": password_record.encoded_hash,
        "password_salt": password_record.salt,
        "password_updated_at": "2026-07-02T10:00:00+00:00",
        "must_change_password": False,
    }
    values.update(overrides)
    tenant_id = values["tenant_id"]
    if store.get_tenant(tenant_id) is None:
        store.create_tenant(tenant_id, display_name=tenant_id)
    return store.create_user(**values)


def _auth_client(monkeypatch, tmp_path):
    db_path = tmp_path / "auth.db"
    monkeypatch.setenv("TRADINGAGENTS_WEB_AUTH_DB", str(db_path))
    monkeypatch.delenv("TRADINGAGENTS_WEB_API_TOKEN", raising=False)
    return TestClient(app), UserStore(db_path)


def _login(client: TestClient, identifier: str = "alice", password: str = "StrongPass123!"):
    response = client.post(
        "/api/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert response.status_code == 200


def _analysis_payload():
    return {"ticker": "NVDA", "date": "2026-07-02"}


def test_session_tenant_overrides_request_tenant(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", tenant_id="alpha")
    _login(client)
    seen: dict[str, str | None] = {}

    monkeypatch.setattr(web_routes, "get_execution_mode", lambda: "external_worker")
    monkeypatch.setattr(web_routes, "get_tenant_id", lambda tenant_id=None: tenant_id)
    monkeypatch.setattr(web_routes, "get_state_backend", lambda: "sqlite")
    monkeypatch.setattr(web_routes, "get_state_location", lambda tenant_id=None: f"/state/{tenant_id}")

    def _status(tenant_id=None):
        seen["tenant_id"] = tenant_id
        return {
            "queue_depth": 0,
            "run_count": 0,
            "worker_running": False,
            "worker_mode": None,
            "worker_last_seen": None,
        }

    monkeypatch.setattr(web_routes, "get_service_status", _status)

    response = client.get(
        "/api/system/status?tenant_id=beta",
        headers={"X-TradingAgents-Tenant": "gamma"},
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "alpha"
    assert seen["tenant_id"] == "alpha"


def test_unauthenticated_request_is_rejected_when_user_auth_enabled(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)

    response = client.get("/api/runs")

    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_viewer_can_get_runs_but_cannot_post_runs(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="viewer")
    _login(client)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    get_response = client.get("/api/runs")
    post_response = client.post("/api/runs", json=_analysis_payload())

    assert get_response.status_code == 200
    assert post_response.status_code == 403


def test_analyst_can_post_runs_but_cannot_put_settings(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="analyst")
    _login(client)

    class _Run:
        run_id = "run-1"
        status = "queued"
        ticker = "NVDA"
        date = "2026-07-02"

    monkeypatch.setattr(web_routes, "create_run", lambda req, loop, tenant_id=None: _Run())

    post_response = client.post("/api/runs", json=_analysis_payload())
    put_response = client.put("/api/settings", json={})

    assert post_response.status_code == 201
    assert put_response.status_code == 403


def test_admin_role_is_allowed_past_middleware_for_admin_paths(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin")
    _login(client)

    settings_response = client.put("/api/settings", json={})
    admin_response = client.put("/api/admin/users", json={})

    assert settings_response.status_code != 403
    assert settings_response.status_code != 401
    assert admin_response.status_code not in {401, 403}


def test_analyst_cannot_access_admin_user_routes(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="analyst")
    _login(client)

    list_response = client.get("/api/admin/users")
    create_response = client.post(
        "/api/admin/users",
        json={
            "username": "new-user",
            "email": "new-user@example.com",
            "display_name": "New User",
            "role": "viewer",
            "password": "AnotherStrong123!",
        },
    )

    assert list_response.status_code == 403
    assert create_response.status_code == 403


def test_viewer_cannot_access_admin_user_routes(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="viewer")
    _login(client)

    list_response = client.get("/api/admin/users")
    create_response = client.post(
        "/api/admin/users",
        json={
            "username": "new-user",
            "email": "new-user@example.com",
            "display_name": "New User",
            "role": "viewer",
            "password": "AnotherStrong123!",
        },
    )

    assert list_response.status_code == 403
    assert create_response.status_code == 403


def test_token_authenticated_request_preserves_legacy_behavior(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="viewer", tenant_id="alpha")
    store.create_tenant("beta", display_name="Beta")
    monkeypatch.setenv("TRADINGAGENTS_WEB_API_TOKEN", "secret-token")
    seen: dict[str, str | None] = {}

    monkeypatch.setattr(web_routes, "get_execution_mode", lambda: "external_worker")
    monkeypatch.setattr(web_routes, "get_tenant_id", lambda tenant_id=None: tenant_id)
    monkeypatch.setattr(web_routes, "get_state_backend", lambda: "sqlite")
    monkeypatch.setattr(web_routes, "get_state_location", lambda tenant_id=None: f"/state/{tenant_id}")

    def _status(tenant_id=None):
        seen["tenant_id"] = tenant_id
        return {
            "queue_depth": 0,
            "run_count": 0,
            "worker_running": False,
            "worker_mode": None,
            "worker_last_seen": None,
        }

    monkeypatch.setattr(web_routes, "get_service_status", _status)

    response = client.get(
        "/api/system/status?tenant_id=beta",
        headers={"Authorization": "Bearer secret-token"},
    )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == "beta"
    assert seen["tenant_id"] == "beta"


def test_forced_password_change_blocks_protected_routes(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="analyst", must_change_password=True)
    _login(client)

    allowed = client.get("/api/auth/me")
    blocked = client.get("/api/runs")

    assert allowed.status_code == 200
    assert blocked.status_code == 403
    assert blocked.json()["code"] == "password_change_required"


def test_disabled_tenant_blocks_existing_session_requests(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    store.create_tenant("tenant-disabled", display_name="Tenant Disabled")
    _create_user(store, role="viewer", tenant_id="tenant-disabled")
    _login(client)
    store.update_tenant("tenant-disabled", disabled=True)
    monkeypatch.setattr(web_routes, "list_runs", lambda tenant_id=None: [])

    response = client.get("/api/runs")

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant is disabled"


def test_token_authenticated_write_request_rejects_disabled_tenant(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    store.create_tenant("tenant-disabled", display_name="Tenant Disabled")
    store.update_tenant("tenant-disabled", disabled=True)
    monkeypatch.setenv("TRADINGAGENTS_WEB_API_TOKEN", "secret-token")

    class _Run:
        run_id = "run-1"
        status = "queued"
        ticker = "NVDA"
        date = "2026-07-02"

    monkeypatch.setattr(web_routes, "create_run", lambda req, loop, tenant_id=None: _Run())

    response = client.post(
        "/api/runs?tenant_id=tenant-disabled",
        headers={"Authorization": "Bearer secret-token"},
        json=_analysis_payload(),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant is disabled"


def test_token_authenticated_write_request_rejects_archived_tenant(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    store.create_tenant("tenant-archived", display_name="Tenant Archived")
    store.update_tenant("tenant-archived", archived=True)
    monkeypatch.setenv("TRADINGAGENTS_WEB_API_TOKEN", "secret-token")

    class _Run:
        run_id = "run-1"
        status = "queued"
        ticker = "NVDA"
        date = "2026-07-02"

    monkeypatch.setattr(web_routes, "create_run", lambda req, loop, tenant_id=None: _Run())

    response = client.post(
        "/api/runs?tenant_id=tenant-archived",
        headers={"Authorization": "Bearer secret-token"},
        json=_analysis_payload(),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant is archived"


def test_legacy_write_request_rejects_disabled_tenant(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    store.create_tenant("tenant-disabled", display_name="Tenant Disabled")
    store.update_tenant("tenant-disabled", disabled=True)

    class _Run:
        run_id = "run-1"
        status = "queued"
        ticker = "NVDA"
        date = "2026-07-02"

    monkeypatch.setattr(web_routes, "create_run", lambda req, loop, tenant_id=None: _Run())

    response = client.post(
        "/api/runs?tenant_id=tenant-disabled",
        json=_analysis_payload(),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant is disabled"


def test_legacy_write_request_rejects_archived_tenant(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    store.create_tenant("tenant-archived", display_name="Tenant Archived")
    store.update_tenant("tenant-archived", archived=True)

    class _Run:
        run_id = "run-1"
        status = "queued"
        ticker = "NVDA"
        date = "2026-07-02"

    monkeypatch.setattr(web_routes, "create_run", lambda req, loop, tenant_id=None: _Run())

    response = client.post(
        "/api/runs?tenant_id=tenant-archived",
        json=_analysis_payload(),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant is archived"


def test_authenticated_me_request_populates_auth_state(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    user = _create_user(store, role="viewer", tenant_id="alpha")
    _login(client)
    observed: dict[str, object | None] = {}
    original = auth_routes._get_current_session

    def _wrapped_get_current_session(request):
        observed["auth_mode"] = getattr(request.state, "auth_mode", None)
        observed["current_user_id"] = getattr(
            getattr(request.state, "current_user", None),
            "id",
            None,
        )
        observed["effective_tenant_id"] = getattr(
            request.state,
            "effective_tenant_id",
            None,
        )
        return original(request)

    monkeypatch.setattr(auth_routes, "_get_current_session", _wrapped_get_current_session)

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert observed == {
        "auth_mode": "session",
        "current_user_id": user.id,
        "effective_tenant_id": "alpha",
    }


def test_unknown_auth_path_is_not_public():
    assert is_public_path("/api/auth/private", "GET") is False
