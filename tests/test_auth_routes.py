"""Route-level tests for browser authentication flows."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import web.auth_routes as auth_routes
from web.app import app
from web.passwords import hash_password, hash_secret
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
    return store.create_user(**values)


def _auth_client(monkeypatch, tmp_path):
    db_path = tmp_path / "auth.db"
    monkeypatch.setenv("TRADINGAGENTS_WEB_AUTH_DB", str(db_path))
    monkeypatch.delenv("TRADINGAGENTS_WEB_API_TOKEN", raising=False)
    return TestClient(app), UserStore(db_path)


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

    expired = store.create_password_reset_token(user.id, hash_secret("111111"), ttl_seconds=-1)
    expired_response = client.post(
        "/api/auth/password-reset/confirm",
        json={"reset_id": expired.id, "code": "111111", "new_password": "EvenStronger456!"},
    )
    assert expired_response.status_code == 400
    assert expired_response.json()["detail"] == "Reset code has expired"

    used = store.create_password_reset_token(user.id, hash_secret("222222"))
    store.mark_password_reset_token_used(used.id)
    used_response = client.post(
        "/api/auth/password-reset/confirm",
        json={"reset_id": used.id, "code": "222222", "new_password": "EvenStronger456!"},
    )
    assert used_response.status_code == 400
    assert used_response.json()["detail"] == "Reset code has already been used"

    limited = store.create_password_reset_token(user.id, hash_secret("333333"))
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
    assert limited_response.json()["detail"] == "Too many reset attempts"


def test_password_reset_confirm_updates_password_and_allows_login(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    user = _create_user(store, must_change_password=True)
    token = store.create_password_reset_token(user.id, hash_secret("444444"))

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
