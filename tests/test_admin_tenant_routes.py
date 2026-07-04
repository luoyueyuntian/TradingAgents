"""Route-level tests for admin tenant management APIs."""

from __future__ import annotations

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


def _login(client: TestClient, identifier: str = "alice", password: str = "StrongPass123!"):
    response = client.post(
        "/api/auth/login",
        json={"identifier": identifier, "password": password},
    )
    assert response.status_code == 200
    return response


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
                "archived": False,
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
                "archived": False,
                "user_count": 2,
                "active_admin_count": 1,
                "created_at": store.get_tenant("tenant-b").created_at,
                "updated_at": store.get_tenant("tenant-b").updated_at,
            },
        ]
    }


def test_create_tenant_creates_initial_admin(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    _login(client)

    response = client.post(
        "/api/admin/tenants",
        json={
            "tenant_id": "  tenant-c  ",
            "display_name": "  Tenant C  ",
            "admin": {
                "username": "  CAdmin  ",
                "email": "  CADMIN@example.com  ",
                "display_name": "  Customer Admin  ",
                "password": "AnotherStrong123!",
            },
        },
    )

    assert response.status_code == 201
    payload = response.json()["tenant"]
    assert payload["tenant_id"] == "tenant-c"
    assert payload["display_name"] == "Tenant C"
    assert payload["user_count"] == 1
    assert payload["active_admin_count"] == 1
    created_tenant = store.get_tenant("tenant-c")
    assert created_tenant is not None
    created_admin = store.get_user_by_identifier("cadmin")
    assert created_admin is not None
    assert created_admin.email == "cadmin@example.com"
    assert created_admin.display_name == "Customer Admin"
    assert created_admin.role == "admin"
    assert created_admin.tenant_id == "tenant-c"
    assert created_admin.must_change_password is True


def test_create_tenant_rolls_back_when_initial_admin_insert_fails(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    _login(client)

    original_duplicate_check = UserStore._raise_for_duplicate_user_field
    calls = {"count": 0}

    def _fail_during_admin_insert(self, conn, field_name, value, excluding_user_id=None):
        calls["count"] += 1
        if calls["count"] == 2:
            raise ValueError("email already exists")
        return original_duplicate_check(self, conn, field_name, value, excluding_user_id=excluding_user_id)

    monkeypatch.setattr(UserStore, "_raise_for_duplicate_user_field", _fail_during_admin_insert)

    response = client.post(
        "/api/admin/tenants",
        json={
            "tenant_id": "tenant-rollback",
            "display_name": "Tenant Rollback",
            "admin": {
                "username": "rollback-admin",
                "email": "rollback-admin@example.com",
                "display_name": "Rollback Admin",
                "password": "AnotherStrong123!",
            },
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "email already exists"
    assert store.get_tenant("tenant-rollback") is None
    assert store.get_user_by_identifier("rollback-admin") is None


def test_disable_and_archive_tenant(monkeypatch, tmp_path):
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
            "archived": True,
        },
    )

    assert update.status_code == 200
    payload = update.json()["tenant"]
    assert payload["display_name"] == "Tenant Bee"
    assert payload["disabled"] is True
    assert payload["archived"] is True

    refreshed = store.get_tenant("tenant-b")
    assert refreshed is not None
    assert refreshed.display_name == "Tenant Bee"
    assert refreshed.disabled is True
    assert refreshed.archived is True

    listed = client.get("/api/admin/tenants")
    assert listed.status_code == 200
    assert [tenant["tenant_id"] for tenant in listed.json()["tenants"]] == ["tenant-a"]


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
