"""Route-level tests for admin tenant management APIs."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from web.app import app
from web.passwords import hash_password
from web.user_store import UserStore


def _auth_client(monkeypatch, tmp_path):
    db_path = tmp_path / "auth.db"
    monkeypatch.setenv("TRADINGAGENTS_WEB_AUTH_DB", str(db_path))
    monkeypatch.delenv("TRADINGAGENTS_WEB_API_TOKEN", raising=False)
    return TestClient(app), UserStore(db_path)


def _create_tenant(store: UserStore, tenant_id: str = "tenant-a", display_name: str = "Tenant A"):
    return store.create_tenant(tenant_id, display_name=display_name)


def _create_user(store: UserStore, **overrides):
    tenant_id = overrides.get("tenant_id", "tenant-a")
    if store.get_tenant(tenant_id) is None:
        _create_tenant(store, tenant_id=tenant_id, display_name=tenant_id.title())

    password_record = hash_password("StrongPass123!")
    values = {
        "username": "alice",
        "email": "alice@example.com",
        "display_name": "Alice Admin",
        "role": "admin",
        "tenant_id": tenant_id,
        "password_hash": password_record.encoded_hash,
        "password_salt": password_record.salt,
        "password_updated_at": "2026-07-02T10:00:00+00:00",
        "must_change_password": False,
    }
    values.update(overrides)
    return store.create_user(**values)


def _login(
    client: TestClient,
    identifier: str = "alice",
    password: str = "StrongPass123!",
    tenant_id: str = "tenant-a",
):
    response = client.post(
        "/api/auth/login",
        json={"tenant_id": tenant_id, "identifier": identifier, "password": password},
    )
    assert response.status_code == 200
    return response


def _now_ms() -> int:
    return int(datetime.now(UTC).timestamp() * 1000)


def test_list_tenants_returns_counts_for_admin(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_tenant(store, tenant_id="tenant-a", display_name="Tenant A")
    _create_tenant(store, tenant_id="tenant-b", display_name="Tenant B")
    _create_user(store, tenant_id="tenant-a")
    _create_user(
        store,
        username="analyst-a",
        email="analyst-a@example.com",
        display_name="Analyst A",
        role="analyst",
        tenant_id="tenant-a",
    )
    _create_user(
        store,
        username="admin-b",
        email="admin-b@example.com",
        display_name="Admin B",
        role="admin",
        tenant_id="tenant-b",
    )
    _create_user(
        store,
        username="disabled-admin-b",
        email="disabled-admin-b@example.com",
        display_name="Disabled Admin B",
        role="admin",
        tenant_id="tenant-b",
        disabled=True,
    )
    _login(client)

    response = client.get("/api/admin/tenants")

    assert response.status_code == 200
    assert response.json() == {
        "tenants": [
            {
                "id": store.get_tenant("tenant-a").id,
                "tenant_id": "tenant-a",
                "display_name": "Tenant A",
                "disabled": False,
                "expires_at": None,
                "status": "active",
                "user_count": 2,
                "active_admin_count": 1,
                "created_at": store.get_tenant("tenant-a").created_at,
                "updated_at": store.get_tenant("tenant-a").updated_at,
            },
            {
                "id": store.get_tenant("tenant-b").id,
                "tenant_id": "tenant-b",
                "display_name": "Tenant B",
                "disabled": False,
                "expires_at": None,
                "status": "active",
                "user_count": 2,
                "active_admin_count": 1,
                "created_at": store.get_tenant("tenant-b").created_at,
                "updated_at": store.get_tenant("tenant-b").updated_at,
            },
        ]
    }


def test_create_tenant_generates_tenant_id_without_bootstrap_admin(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    _login(client)
    expires_at = _now_ms() + 86_400_000

    response = client.post(
        "/api/admin/tenants",
        json={
            "display_name": "  Tenant C  ",
            "expires_at": expires_at,
        },
    )

    assert response.status_code == 201
    payload = response.json()["tenant"]
    assert payload["tenant_id"] == "tenant-c"
    assert payload["display_name"] == "Tenant C"
    assert payload["expires_at"] == expires_at
    assert payload["status"] == "active"
    assert payload["user_count"] == 0
    assert payload["active_admin_count"] == 0
    created_tenant = store.get_tenant("tenant-c")
    assert created_tenant is not None
    assert created_tenant.expires_at == expires_at
    assert store.list_users("tenant-c") == []


def test_create_tenant_generates_unique_slug_for_reused_display_name(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    _login(client)

    first = client.post(
        "/api/admin/tenants",
        json={
            "display_name": "Acme Capital",
        },
    )
    second = client.post(
        "/api/admin/tenants",
        json={
            "display_name": "Acme Capital",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["tenant"]["tenant_id"] == "acme-capital"
    assert second.json()["tenant"]["tenant_id"] == "acme-capital-2"


def test_update_tenant_supports_display_name_disabled_and_expires_at(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    _create_tenant(store, tenant_id="tenant-b", display_name="Tenant B")
    _create_user(
        store,
        username="admin-b",
        email="admin-b@example.com",
        display_name="Admin B",
        role="admin",
        tenant_id="tenant-b",
    )
    _login(client)
    expires_at = _now_ms() + 86_400_000

    detail = client.get("/api/admin/tenants/tenant-b")
    assert detail.status_code == 200
    assert detail.json()["tenant"]["tenant_id"] == "tenant-b"
    assert detail.json()["tenant"]["user_count"] == 1
    assert detail.json()["tenant"]["active_admin_count"] == 1

    update = client.patch(
        "/api/admin/tenants/tenant-b",
        json={
            "display_name": "  Tenant Bee  ",
            "disabled": True,
            "expires_at": expires_at,
        },
    )

    assert update.status_code == 200
    payload = update.json()["tenant"]
    assert payload["display_name"] == "Tenant Bee"
    assert payload["disabled"] is True
    assert payload["expires_at"] == expires_at
    assert payload["status"] == "disabled"

    refreshed = store.get_tenant("tenant-b")
    assert refreshed is not None
    assert refreshed.display_name == "Tenant Bee"
    assert refreshed.disabled is True
    assert refreshed.expires_at == expires_at

    listed = client.get("/api/admin/tenants")
    assert listed.status_code == 200
    assert [tenant["tenant_id"] for tenant in listed.json()["tenants"]] == ["tenant-a", "tenant-b"]


def test_list_tenants_filters_by_name_status_and_created_range(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    _create_tenant(store, tenant_id="tenant-alpha", display_name="Alpha Trading")
    _create_tenant(store, tenant_id="tenant-beta", display_name="Beta Research")
    _create_tenant(store, tenant_id="tenant-gamma", display_name="Gamma Capital")
    store.update_tenant("tenant-beta", disabled=True)
    store.update_tenant("tenant-gamma", expires_at=_now_ms() - 60_000)
    alpha_created_at = int(datetime(2026, 7, 3, tzinfo=UTC).timestamp() * 1000)
    beta_created_at = int(datetime(2026, 7, 9, tzinfo=UTC).timestamp() * 1000)
    gamma_created_at = int(datetime(2026, 7, 12, tzinfo=UTC).timestamp() * 1000)

    with store._connect() as conn:  # noqa: SLF001
        conn.execute(
            "UPDATE tenants SET created_at = ?, updated_at = ? WHERE tenant_id = ?",
            (alpha_created_at, alpha_created_at, "tenant-alpha"),
        )
        conn.execute(
            "UPDATE tenants SET created_at = ?, updated_at = ? WHERE tenant_id = ?",
            (beta_created_at, beta_created_at, "tenant-beta"),
        )
        conn.execute(
            "UPDATE tenants SET created_at = ?, updated_at = ? WHERE tenant_id = ?",
            (gamma_created_at, gamma_created_at, "tenant-gamma"),
        )
    _login(client)

    by_name = client.get("/api/admin/tenants?name=gamma")
    disabled = client.get("/api/admin/tenants?status=disabled")
    expired = client.get("/api/admin/tenants?status=expired")
    created_range = client.get("/api/admin/tenants?created_from=2026-07-08&created_to=2026-07-11")

    assert by_name.status_code == 200
    assert [tenant["tenant_id"] for tenant in by_name.json()["tenants"]] == ["tenant-gamma"]
    assert disabled.status_code == 200
    assert [tenant["tenant_id"] for tenant in disabled.json()["tenants"]] == ["tenant-beta"]
    assert expired.status_code == 200
    assert [tenant["tenant_id"] for tenant in expired.json()["tenants"]] == ["tenant-gamma"]
    assert created_range.status_code == 200
    assert [tenant["tenant_id"] for tenant in created_range.json()["tenants"]] == ["tenant-beta"]


def test_batch_disable_skips_disabled_and_expired_tenants(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False, tenant_id="tenant-a")
    _create_user(
        store,
        username="tenant-c-admin",
        email="tenant-c-admin@example.com",
        display_name="Tenant C Admin",
        role="admin",
        tenant_id="tenant-c",
        must_change_password=False,
    )
    _create_tenant(store, tenant_id="tenant-b", display_name="Tenant B")
    store.update_tenant("tenant-b", disabled=True)
    _create_tenant(store, tenant_id="tenant-d", display_name="Tenant D")
    store.update_tenant("tenant-d", expires_at=_now_ms() - 60_000)
    _login(client)

    response = client.post(
        "/api/admin/tenants/batch-disable",
        json={"tenant_ids": ["tenant-a", "tenant-b", "tenant-d"]},
    )

    assert response.status_code == 200
    assert response.json() == {
        "updated_count": 1,
        "skipped_count": 2,
        "skipped_tenant_ids": ["tenant-b", "tenant-d"],
    }
    assert store.get_tenant("tenant-a").disabled is True
    assert store.get_tenant("tenant-b").disabled is True
    assert store.get_tenant("tenant-d").disabled is False


def test_tenant_update_prevents_last_login_capable_admin_tenant_lockout(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    _create_user(
        store,
        username="tenant-b-admin",
        email="tenant-b-admin@example.com",
        display_name="Tenant B Admin",
        role="admin",
        tenant_id="tenant-b",
        must_change_password=False,
    )
    store.update_tenant("tenant-a", disabled=True)
    _login(client, identifier="tenant-b-admin", tenant_id="tenant-b")

    response = client.patch("/api/admin/tenants/tenant-b", json={"disabled": True})

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot disable or expire the last tenant with a login-capable admin"
    refreshed = store.get_tenant("tenant-b")
    assert refreshed is not None
    assert refreshed.disabled is False


@pytest.mark.parametrize("field_name", ["display_name", "disabled"])
def test_tenant_update_rejects_explicit_null_fields(monkeypatch, tmp_path, field_name: str):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    _login(client)
    original = store.get_tenant("tenant-a")
    assert original is not None

    response = client.patch("/api/admin/tenants/tenant-a", json={field_name: None})

    assert response.status_code == 400
    assert response.json()["detail"] == f"{field_name} must not be null"
    refreshed = store.get_tenant("tenant-a")
    assert refreshed is not None
    assert refreshed.display_name == original.display_name
    assert refreshed.disabled is False


def test_tenant_update_allows_clearing_expires_at(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    store.update_tenant("tenant-a", expires_at=_now_ms() + 86_400_000)
    _login(client)

    response = client.patch("/api/admin/tenants/tenant-a", json={"expires_at": None})

    assert response.status_code == 200
    payload = response.json()["tenant"]
    assert payload["expires_at"] is None
    assert payload["status"] == "active"
    refreshed = store.get_tenant("tenant-a")
    assert refreshed is not None
    assert refreshed.expires_at is None


def test_tenant_scoped_user_list_returns_only_target_tenant_users(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    tenant_b_admin = _create_user(
        store,
        username="tenant-b-admin",
        email="tenant-b-admin@example.com",
        display_name="Tenant B Admin",
        role="admin",
        tenant_id="tenant-b",
        must_change_password=False,
    )
    _create_user(
        store,
        username="tenant-b-analyst",
        email="tenant-b-analyst@example.com",
        display_name="Tenant B Analyst",
        role="analyst",
        tenant_id="tenant-b",
        must_change_password=False,
    )
    _create_user(
        store,
        username="tenant-c-user",
        email="tenant-c-user@example.com",
        display_name="Tenant C User",
        role="viewer",
        tenant_id="tenant-c",
        must_change_password=False,
    )
    _login(client, identifier="tenant-b-admin", tenant_id="tenant-b")

    response = client.get("/api/admin/tenants/tenant-b/users")

    assert response.status_code == 200
    payload = response.json()
    assert [user["username"] for user in payload["users"]] == ["tenant-b-admin", "tenant-b-analyst"]
    assert all(user["tenant_id"] == "tenant-b" for user in payload["users"])
    assert payload["users"][0]["id"] == tenant_b_admin.id


def test_tenant_scoped_user_create_writes_to_target_tenant(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", tenant_id="tenant-b", must_change_password=False)
    _login(client, tenant_id="tenant-b")

    response = client.post(
        "/api/admin/tenants/tenant-b/users",
        json={
            "username": "  scoped-user  ",
            "email": "  scoped-user@example.com  ",
            "display_name": "  Scoped User  ",
            "role": " viewer ",
            "password": "AnotherStrong123!",
            "expires_at": "",
        },
    )

    assert response.status_code == 201
    payload = response.json()["user"]
    assert payload["username"] == "scoped-user"
    assert payload["email"] == "scoped-user@example.com"
    assert payload["display_name"] == "Scoped User"
    assert payload["role"] == "viewer"
    assert payload["tenant_id"] == "tenant-b"
    created = store.get_user(payload["id"])
    assert created is not None
    assert created.tenant_id == "tenant-b"
    assert created.must_change_password is True


def test_tenant_scoped_user_create_rejects_disabled_tenant(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    _create_tenant(store, tenant_id="tenant-b", display_name="Tenant B")
    store.update_tenant("tenant-b", disabled=True)
    _login(client)

    response = client.post(
        "/api/admin/tenants/tenant-b/users",
        json={
            "username": "disabled-user",
            "email": "disabled-user@example.com",
            "display_name": "Disabled User",
            "role": "viewer",
            "password": "AnotherStrong123!",
            "expires_at": "",
        },
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Membership management requires the active tenant"
    assert store.get_user_by_identifier("disabled-user") is None


def test_tenant_scoped_user_delete_protects_last_active_admin(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    sole_tenant_b_admin = _create_user(
        store,
        username="tenant-b-admin",
        email="tenant-b-admin@example.com",
        display_name="Tenant B Admin",
        role="admin",
        tenant_id="tenant-b",
        must_change_password=False,
    )
    _login(client, identifier="tenant-b-admin", tenant_id="tenant-b")

    response = client.delete(f"/api/admin/tenants/tenant-b/users/{sole_tenant_b_admin.id}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot remove the last active admin from tenant"


def test_tenant_scoped_user_update_rejects_expired_tenant(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    expired_user = _create_user(
        store,
        username="tenant-b-viewer",
        email="tenant-b-viewer@example.com",
        display_name="Tenant B Viewer",
        role="viewer",
        tenant_id="tenant-b",
        must_change_password=False,
    )
    store.update_tenant("tenant-b", expires_at=_now_ms() - 60_000)
    _login(client)

    response = client.patch(
        f"/api/admin/tenants/tenant-b/users/{expired_user.id}",
        json={"role": "analyst"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Membership management requires the active tenant"
    refreshed = store.get_user(expired_user.id)
    assert refreshed is not None
    assert refreshed.role == "viewer"


def test_tenant_scoped_user_delete_rejects_expired_tenant(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    expired_user = _create_user(
        store,
        username="tenant-b-viewer",
        email="tenant-b-viewer@example.com",
        display_name="Tenant B Viewer",
        role="viewer",
        tenant_id="tenant-b",
        must_change_password=False,
    )
    store.update_tenant("tenant-b", expires_at=_now_ms() - 60_000)
    _login(client)

    response = client.delete(f"/api/admin/tenants/tenant-b/users/{expired_user.id}")

    assert response.status_code == 403
    assert response.json()["detail"] == "Membership management requires the active tenant"
    assert store.get_user(expired_user.id) is not None


def test_tenant_scoped_user_update_and_delete_reject_out_of_tenant_user_ids(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", tenant_id="tenant-b", must_change_password=False)
    other_tenant_user = _create_user(
        store,
        username="tenant-c-user",
        email="tenant-c-user@example.com",
        display_name="Tenant C User",
        role="viewer",
        tenant_id="tenant-c",
        must_change_password=False,
    )
    _login(client, tenant_id="tenant-b")

    update_response = client.patch(
        f"/api/admin/tenants/tenant-b/users/{other_tenant_user.id}",
        json={"role": "analyst"},
    )
    delete_response = client.delete(f"/api/admin/tenants/tenant-b/users/{other_tenant_user.id}")

    assert update_response.status_code == 404
    assert update_response.json()["detail"] == "User not found"
    assert delete_response.status_code == 404
    assert delete_response.json()["detail"] == "User not found"


@pytest.mark.parametrize("method", ["get", "patch"])
def test_malformed_tenant_id_returns_400(monkeypatch, tmp_path, method: str):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    _login(client)

    path = "/api/admin/tenants/bad!id"
    if method == "get":
        response = client.get(path)
    else:
        response = client.patch(path, json={"display_name": "Tenant Bad"})

    assert response.status_code == 400
    assert response.json()["detail"] == "tenant_id must be 1-64 chars using letters, numbers, dot, dash, or underscore"


@pytest.mark.parametrize('method,path,payload', [
    ('get', '/users', None),
    ('post', '/users', {'username': 'intruder', 'email': 'intruder@example.com', 'role': 'admin', 'display_name': 'Intruder', 'password': 'StrongPass123!'}),
    ('post', '/users/memberships', {'email': 'alice@example.com', 'role': 'admin', 'username': 'alice'}),
    ('patch', '/users/target', {'role': 'admin'}),
    ('delete', '/users/target', None),
])
def test_admin_cannot_manage_other_tenant_memberships(monkeypatch, tmp_path, method, path, payload):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    _create_tenant(store, 'tenant-b')
    _login(client)
    response = client.request(method, '/api/admin/tenants/tenant-b' + path, json=payload)
    assert response.status_code == 403
