"""Route-level tests for browser authentication flows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import web.auth_routes as auth_routes
from web.app import app
from web.passwords import hash_password, hash_verification_code
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
        "must_change_password": True,
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
    return response


def test_login_rejects_invalid_credentials(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)

    response = client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_login_sets_session_cookie(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)

    response = client.post(
        "/api/auth/login",
        json={"identifier": "alice@example.com", "password": "StrongPass123!"},
    )

    assert response.status_code == 200
    assert response.cookies.get("tradingagents_session")


def test_login_marks_session_cookie_secure_for_forwarded_https(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)

    response = client.post(
        "/api/auth/login",
        json={"identifier": "alice@example.com", "password": "StrongPass123!"},
        headers={"X-Forwarded-Proto": "https"},
    )

    assert response.status_code == 200
    assert "secure" in response.headers["set-cookie"].lower()


def test_me_returns_authenticated_user_summary(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    user = _create_user(store)

    login = client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "StrongPass123!"},
    )
    assert login.status_code == 200

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    assert response.json()["user"]["id"] == user.id
    assert response.json()["user"]["must_change_password"] is True


def test_logout_clears_session_cookie(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)

    login = client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "StrongPass123!"},
    )
    assert login.status_code == 200

    response = client.post("/api/auth/logout")

    assert response.status_code == 200
    assert "tradingagents_session=" in response.headers["set-cookie"]
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_login_rejects_disabled_user_with_clear_403(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, disabled=True)

    response = client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "StrongPass123!"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User account is disabled"


def test_login_rejects_expired_user_with_clear_403(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(
        store,
        expires_at=(datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
    )

    response = client.post(
        "/api/auth/login",
        json={"identifier": "alice@example.com", "password": "StrongPass123!"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "User account has expired"


def test_login_rejects_disabled_tenant_with_clear_403(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    store.create_tenant("tenant-disabled", display_name="Tenant Disabled")
    _create_user(store, tenant_id="tenant-disabled")
    store.update_tenant("tenant-disabled", disabled=True)

    response = client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "StrongPass123!"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant is disabled"


def test_login_rejects_archived_tenant_with_clear_403(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    store.create_tenant("tenant-archived", display_name="Tenant Archived")
    _create_user(store, tenant_id="tenant-archived")
    store.update_tenant("tenant-archived", archived=True)

    response = client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "StrongPass123!"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant is archived"


def test_me_rejects_missing_or_expired_session(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    user = _create_user(store)
    expired_session_id, _session = store.create_session(user.id, ttl_seconds=-1)

    missing = client.get("/api/auth/me")
    assert missing.status_code == 401
    assert missing.json()["detail"] == "Unauthorized"

    client.cookies.set("tradingagents_session", expired_session_id)
    expired = client.get("/api/auth/me")

    assert expired.status_code == 401
    assert expired.json()["detail"] == "Unauthorized"


def test_change_password_rejects_wrong_old_password(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    login = client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "StrongPass123!"},
    )
    assert login.status_code == 200

    response = client.post(
        "/api/auth/change-password",
        json={"old_password": "wrong-password", "new_password": "EvenStronger456!"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


def test_change_password_rejects_weak_new_password(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    login = client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "StrongPass123!"},
    )
    assert login.status_code == 200

    response = client.post(
        "/api/auth/change-password",
        json={"old_password": "StrongPass123!", "new_password": "short"},
    )

    assert response.status_code == 400
    assert "at least 10 characters" in response.json()["detail"]


def test_change_password_updates_hash_and_clears_must_change(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    user = _create_user(store, must_change_password=True)
    login = client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "StrongPass123!"},
    )
    assert login.status_code == 200

    response = client.post(
        "/api/auth/change-password",
        json={"old_password": "StrongPass123!", "new_password": "EvenStronger456!"},
    )

    assert response.status_code == 200
    refreshed = store.get_user(user.id)
    assert refreshed is not None
    assert refreshed.must_change_password is False
    assert refreshed.password_updated_at is not None

    relogin = client.post(
        "/api/auth/login",
        json={"identifier": "alice", "password": "EvenStronger456!"},
    )
    assert relogin.status_code == 200


def test_password_reset_request_reports_unavailable_without_smtp(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)

    response = client.post(
        "/api/auth/password-reset/request",
        json={"email": "alice@example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "available": False,
        "reset_id": None,
        "detail": "Password reset is unavailable",
    }


def test_password_reset_request_is_non_enumerating_and_uses_fake_sender(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    sent_messages = []
    monkeypatch.setenv("TRADINGAGENTS_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("TRADINGAGENTS_SMTP_PORT", "2525")
    monkeypatch.setenv("TRADINGAGENTS_SMTP_FROM", "noreply@example.com")
    monkeypatch.setattr(auth_routes, "send_password_reset_email", sent_messages.append)

    existing = client.post(
        "/api/auth/password-reset/request",
        json={"email": "alice@example.com"},
    )
    missing = client.post(
        "/api/auth/password-reset/request",
        json={"email": "missing@example.com"},
    )

    assert existing.status_code == 200
    assert existing.json()["available"] is True
    assert existing.json()["reset_id"]
    assert missing.status_code == 200
    assert missing.json()["available"] is True
    assert missing.json()["reset_id"]
    assert len(sent_messages) == 1
    assert sent_messages[0].to_email == "alice@example.com"
    assert sent_messages[0].code.isdigit()
    assert len(sent_messages[0].code) == 6


def test_password_reset_request_hides_smtp_failures_for_existing_accounts(
    monkeypatch, tmp_path
):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store)
    monkeypatch.setenv("TRADINGAGENTS_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("TRADINGAGENTS_SMTP_PORT", "2525")
    monkeypatch.setenv("TRADINGAGENTS_SMTP_FROM", "noreply@example.com")

    def _fail_send(_message):
        raise OSError("smtp unavailable")

    monkeypatch.setattr(auth_routes, "send_password_reset_email", _fail_send)

    existing = client.post(
        "/api/auth/password-reset/request",
        json={"email": "alice@example.com"},
    )
    missing = client.post(
        "/api/auth/password-reset/request",
        json={"email": "missing@example.com"},
    )

    assert existing.status_code == 200
    assert missing.status_code == 200
    assert existing.json()["available"] is True
    assert missing.json()["available"] is True
    assert existing.json()["reset_id"]
    assert missing.json()["reset_id"]


def test_password_reset_request_treats_username_input_as_non_enumerating_miss(
    monkeypatch, tmp_path
):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, username="alice-user", email="alice@example.com")
    sent_messages = []
    monkeypatch.setenv("TRADINGAGENTS_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("TRADINGAGENTS_SMTP_PORT", "2525")
    monkeypatch.setenv("TRADINGAGENTS_SMTP_FROM", "noreply@example.com")
    monkeypatch.setattr(auth_routes, "send_password_reset_email", sent_messages.append)

    username_response = client.post(
        "/api/auth/password-reset/request",
        json={"email": "alice-user"},
    )
    missing_response = client.post(
        "/api/auth/password-reset/request",
        json={"email": "missing@example.com"},
    )

    assert username_response.status_code == 200
    assert username_response.json()["available"] is True
    assert username_response.json()["reset_id"]
    assert username_response.json() == missing_response.json() | {
        "reset_id": username_response.json()["reset_id"]
    }
    assert len(sent_messages) == 0


def test_password_reset_request_matches_stored_email_without_dot_heuristic(
    monkeypatch, tmp_path
):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, email="alice@corp")
    sent_messages = []
    monkeypatch.setenv("TRADINGAGENTS_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("TRADINGAGENTS_SMTP_PORT", "2525")
    monkeypatch.setenv("TRADINGAGENTS_SMTP_FROM", "noreply@example.com")
    monkeypatch.setattr(auth_routes, "send_password_reset_email", sent_messages.append)

    response = client.post(
        "/api/auth/password-reset/request",
        json={"email": "alice@corp"},
    )

    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["reset_id"]
    assert len(sent_messages) == 1
    assert sent_messages[0].to_email == "alice@corp"
    assert sent_messages[0].code.isdigit()
    assert len(sent_messages[0].code) == 6


def test_password_reset_request_ignores_username_shadowing_email_value(
    monkeypatch, tmp_path
):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(
        store,
        username="alice@example.com",
        email="shadow-owner@example.net",
    )
    _create_user(
        store,
        username="real-owner",
        email="alice@example.com",
        display_name="Real Owner",
    )
    sent_messages = []
    monkeypatch.setenv("TRADINGAGENTS_SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("TRADINGAGENTS_SMTP_PORT", "2525")
    monkeypatch.setenv("TRADINGAGENTS_SMTP_FROM", "noreply@example.com")
    monkeypatch.setattr(auth_routes, "send_password_reset_email", sent_messages.append)

    response = client.post(
        "/api/auth/password-reset/request",
        json={"email": "alice@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["reset_id"]
    assert len(sent_messages) == 1
    assert sent_messages[0].to_email == "alice@example.com"
    assert sent_messages[0].code.isdigit()
    assert len(sent_messages[0].code) == 6


def test_password_reset_confirm_rejects_invalid_expired_used_and_attempt_limited_codes(
    monkeypatch, tmp_path
):
    client, store = _auth_client(monkeypatch, tmp_path)
    user = _create_user(store)

    invalid = client.post(
        "/api/auth/password-reset/confirm",
        json={"reset_id": "missing-reset", "code": "123456", "new_password": "EvenStronger456!"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["detail"] == "Invalid or expired reset code"

    expired = store.create_password_reset_token(user.id, hash_verification_code("111111"), ttl_seconds=-1)
    expired_response = client.post(
        "/api/auth/password-reset/confirm",
        json={"reset_id": expired.id, "code": "111111", "new_password": "EvenStronger456!"},
    )
    assert expired_response.status_code == 400
    assert expired_response.json()["detail"] == "Invalid or expired reset code"

    used = store.create_password_reset_token(user.id, hash_verification_code("222222"))
    store.mark_password_reset_token_used(used.id)
    used_response = client.post(
        "/api/auth/password-reset/confirm",
        json={"reset_id": used.id, "code": "222222", "new_password": "EvenStronger456!"},
    )
    assert used_response.status_code == 400
    assert used_response.json()["detail"] == "Invalid or expired reset code"

    limited = store.create_password_reset_token(user.id, hash_verification_code("333333"))
    for _ in range(5):
        wrong = client.post(
            "/api/auth/password-reset/confirm",
            json={"reset_id": limited.id, "code": "000000", "new_password": "EvenStronger456!"},
        )
        assert wrong.status_code == 400
        assert wrong.json()["detail"] == "Invalid or expired reset code"

    limited_response = client.post(
        "/api/auth/password-reset/confirm",
        json={"reset_id": limited.id, "code": "333333", "new_password": "EvenStronger456!"},
    )
    assert limited_response.status_code == 400
    assert limited_response.json()["detail"] == "Invalid or expired reset code"


def test_password_reset_confirm_does_not_distinguish_fake_and_limited_reset_ids(
    monkeypatch, tmp_path
):
    client, store = _auth_client(monkeypatch, tmp_path)
    user = _create_user(store)
    real = store.create_password_reset_token(user.id, hash_verification_code("333333"))
    fake_reset_id = "f" * 32

    for _ in range(5):
        response = client.post(
            "/api/auth/password-reset/confirm",
            json={"reset_id": real.id, "code": "000000", "new_password": "EvenStronger456!"},
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid or expired reset code"

    real_limited = client.post(
        "/api/auth/password-reset/confirm",
        json={"reset_id": real.id, "code": "333333", "new_password": "EvenStronger456!"},
    )
    fake = client.post(
        "/api/auth/password-reset/confirm",
        json={"reset_id": fake_reset_id, "code": "333333", "new_password": "EvenStronger456!"},
    )

    assert real_limited.status_code == 400
    assert fake.status_code == 400
    assert real_limited.json()["detail"] == fake.json()["detail"] == "Invalid or expired reset code"


def test_password_reset_confirm_updates_password_and_allows_login(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    user = _create_user(store, must_change_password=True)
    token = store.create_password_reset_token(user.id, hash_verification_code("444444"))

    response = client.post(
        "/api/auth/password-reset/confirm",
        json={"reset_id": token.id, "code": "444444", "new_password": "EvenStronger456!"},
    )

    assert response.status_code == 200
    refreshed = store.get_user(user.id)
    assert refreshed is not None
    assert refreshed.must_change_password is False
    assert refreshed.password_updated_at is not None

    login = client.post(
        "/api/auth/login",
        json={"identifier": "alice@example.com", "password": "EvenStronger456!"},
    )
    assert login.status_code == 200


def test_admin_lists_only_tenant_users(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    admin = _create_user(store, role="admin", tenant_id="tenant-a", must_change_password=False)
    _create_user(
        store,
        username="bravo",
        email="bravo@example.com",
        display_name="Bravo",
        tenant_id="tenant-a",
    )
    _create_user(
        store,
        username="charlie",
        email="charlie@example.com",
        display_name="Charlie",
        tenant_id="tenant-b",
    )
    _login(client)

    response = client.get("/api/admin/users")

    assert response.status_code == 200
    payload = response.json()
    assert [user["username"] for user in payload["users"]] == ["alice", "bravo"]
    assert all(user["tenant_id"] == "tenant-a" for user in payload["users"])
    assert payload["users"][0]["id"] == admin.id
    assert "password_hash" not in payload["users"][0]
    assert "password_salt" not in payload["users"][0]


def test_admin_can_create_user(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    _login(client)

    response = client.post(
        "/api/admin/users",
        json={
            "username": "  NEWUSER  ",
            "email": "  NEWUSER@example.com  ",
            "display_name": "  New User  ",
            "role": " ADMIN ",
            "password": "AnotherStrong123!",
            "expires_at": "",
        },
    )

    assert response.status_code == 201
    payload = response.json()["user"]
    assert payload["username"] == "newuser"
    assert payload["email"] == "newuser@example.com"
    assert payload["display_name"] == "New User"
    assert payload["role"] == "admin"
    assert payload["tenant_id"] == "tenant-a"
    assert payload["expires_at"] is None
    assert payload["must_change_password"] is True
    created = store.get_user(payload["id"])
    assert created is not None
    assert created.must_change_password is True
    assert created.tenant_id == "tenant-a"


def test_admin_create_user_rejects_duplicate_username_and_email(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    _create_user(
        store,
        username="existing",
        email="existing@example.com",
        display_name="Existing User",
    )
    _login(client)

    duplicate_username = client.post(
        "/api/admin/users",
        json={
            "username": "Existing",
            "email": "new@example.com",
            "display_name": "New User",
            "role": "viewer",
            "password": "AnotherStrong123!",
        },
    )
    duplicate_email = client.post(
        "/api/admin/users",
        json={
            "username": "new-user",
            "email": "EXISTING@example.com",
            "display_name": "New User",
            "role": "viewer",
            "password": "AnotherStrong123!",
        },
    )

    assert duplicate_username.status_code == 409
    assert duplicate_username.json()["detail"] == "username already exists"
    assert duplicate_email.status_code == 409
    assert duplicate_email.json()["detail"] == "email already exists"


def test_admin_can_update_role_and_expiry_within_tenant(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    target = _create_user(
        store,
        username="target",
        email="target@example.com",
        display_name="Target User",
        role="viewer",
        must_change_password=False,
    )
    other_tenant_user = _create_user(
        store,
        username="other-tenant",
        email="other-tenant@example.com",
        display_name="Other Tenant",
        tenant_id="tenant-b",
        must_change_password=False,
    )
    _login(client)

    response = client.patch(
        f"/api/admin/users/{target.id}",
        json={
            "role": " ANALYST ",
            "display_name": "  Target Person  ",
            "expires_at": "2030-01-02T03:04:05+00:00",
        },
    )
    missing = client.patch(
        f"/api/admin/users/{other_tenant_user.id}",
        json={"role": "viewer"},
    )

    assert response.status_code == 200
    payload = response.json()["user"]
    assert payload["role"] == "analyst"
    assert payload["display_name"] == "Target Person"
    assert payload["expires_at"] == "2030-01-02T03:04:05+00:00"
    assert missing.status_code == 404


def test_admin_disable_invalidates_sessions(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    target = _create_user(
        store,
        username="target",
        email="target@example.com",
        display_name="Target User",
        role="analyst",
        must_change_password=False,
    )
    raw_session_id, _session = store.create_session(target.id)
    _login(client)

    response = client.patch(
        f"/api/admin/users/{target.id}",
        json={"disabled": True},
    )

    assert response.status_code == 200
    assert response.json()["user"]["disabled"] is True
    assert store.get_session(raw_session_id) is None


def test_admin_password_reset_sets_must_change_and_invalidates_sessions(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    target = _create_user(
        store,
        username="target",
        email="target@example.com",
        display_name="Target User",
        role="analyst",
        must_change_password=False,
    )
    raw_session_id, _session = store.create_session(target.id)
    _login(client)

    response = client.patch(
        f"/api/admin/users/{target.id}",
        json={"password": "ResetStrong123!"},
    )

    assert response.status_code == 200
    refreshed = store.get_user(target.id)
    assert refreshed is not None
    assert refreshed.must_change_password is True
    assert refreshed.password_updated_at is not None
    assert store.get_session(raw_session_id) is None


def test_admin_password_reset_uses_atomic_store_helper(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    target = _create_user(
        store,
        username="target",
        email="target@example.com",
        display_name="Target User",
        role="analyst",
        must_change_password=False,
    )
    store.create_session(target.id)
    _login(client)

    def _fail_direct_update(self, user_id, **fields):
        raise AssertionError(f"non-atomic update_user path used for {user_id}: {sorted(fields)}")

    monkeypatch.setattr(UserStore, "update_user", _fail_direct_update)

    response = client.patch(
        f"/api/admin/users/{target.id}",
        json={"password": "ResetStrong123!"},
    )

    assert response.status_code == 200
    assert response.json()["user"]["must_change_password"] is True


def test_admin_delete_soft_disables_user(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    target = _create_user(
        store,
        username="target",
        email="target@example.com",
        display_name="Target User",
        role="viewer",
        must_change_password=False,
    )
    raw_session_id, _session = store.create_session(target.id)
    _login(client)

    response = client.delete(f"/api/admin/users/{target.id}")

    assert response.status_code == 200
    refreshed = store.get_user(target.id)
    assert refreshed is not None
    assert refreshed.disabled is True
    assert store.get_session(raw_session_id) is None


def test_admin_cannot_disable_delete_or_demote_last_active_admin(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    sole_admin = _create_user(store, role="admin", must_change_password=False)
    _login(client)

    disable_response = client.patch(
        f"/api/admin/users/{sole_admin.id}",
        json={"disabled": True},
    )
    demote_response = client.patch(
        f"/api/admin/users/{sole_admin.id}",
        json={"role": "viewer"},
    )
    delete_response = client.delete(f"/api/admin/users/{sole_admin.id}")

    assert disable_response.status_code == 400
    assert disable_response.json()["detail"] == "Cannot remove the last active admin from tenant"
    assert demote_response.status_code == 400
    assert demote_response.json()["detail"] == "Cannot remove the last active admin from tenant"
    assert delete_response.status_code == 400
    assert delete_response.json()["detail"] == "Cannot remove the last active admin from tenant"


def test_admin_cannot_expire_last_active_admin_into_the_past(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    sole_admin = _create_user(store, role="admin", must_change_password=False)
    _login(client)

    response = client.patch(
        f"/api/admin/users/{sole_admin.id}",
        json={"expires_at": "2020-01-01T00:00:00+00:00"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot remove the last active admin from tenant"


@pytest.mark.parametrize("field_name", ["display_name", "role", "disabled"])
def test_admin_user_update_rejects_explicit_null_fields(monkeypatch, tmp_path, field_name: str):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, role="admin", must_change_password=False)
    target = _create_user(
        store,
        username="target",
        email="target@example.com",
        display_name="Target User",
        role="viewer",
        must_change_password=False,
    )
    _login(client)

    response = client.patch(f"/api/admin/users/{target.id}", json={field_name: None})

    assert response.status_code == 400
    assert response.json()["detail"] == f"{field_name} must not be null"
    refreshed = store.get_user(target.id)
    assert refreshed is not None
    assert refreshed.display_name == "Target User"
    assert refreshed.role == "viewer"
    assert refreshed.disabled is False
