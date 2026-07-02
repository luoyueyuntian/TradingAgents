"""Tests for the SQLite-backed web user store."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

import web.user_store as user_store_module
from tradingagents.service import web_state as web_state_module
from web.passwords import hash_secret, verify_password
from web.user_store import UserStore

EXPECTED_SCHEMA = {
    "users": [
        "id",
        "username",
        "email",
        "display_name",
        "role",
        "tenant_id",
        "password_hash",
        "password_salt",
        "password_updated_at",
        "must_change_password",
        "expires_at",
        "disabled",
        "created_at",
        "updated_at",
        "last_login_at",
    ],
    "sessions": [
        "id_hash",
        "user_id",
        "created_at",
        "last_seen_at",
        "expires_at",
    ],
    "password_reset_tokens": [
        "id",
        "user_id",
        "code_hash",
        "created_at",
        "expires_at",
        "used_at",
        "attempt_count",
    ],
    "audit_events": [
        "id",
        "actor_user_id",
        "target_user_id",
        "tenant_id",
        "event_type",
        "created_at",
        "metadata",
    ],
}


def _table_columns(db_path, table_name):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return [row[1] for row in rows]


def _create_user(store, **overrides):
    values = {
        "username": "alice",
        "email": "alice@example.com",
        "display_name": "Alice Analyst",
        "role": "analyst",
        "tenant_id": "tenant-a",
        "password_hash": "hash-1",
        "password_salt": "salt-1",
        "must_change_password": False,
    }
    values.update(overrides)
    return store.create_user(**values)


def _parse_timestamp(value):
    return datetime.fromisoformat(value)


def test_ensure_schema_creates_auth_tables_and_enables_wal(tmp_path):
    db_path = tmp_path / "auth.db"

    UserStore(db_path).ensure_schema()

    with sqlite3.connect(db_path) as conn:
        table_names = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]

    assert set(EXPECTED_SCHEMA).issubset(table_names)
    assert journal_mode == "wal"
    for table_name, expected_columns in EXPECTED_SCHEMA.items():
        assert _table_columns(db_path, table_name) == expected_columns


def test_create_user_persists_record_and_looks_up_identifier_case_insensitively(tmp_path):
    store = UserStore(tmp_path / "auth.db")

    user = _create_user(store, username="Alice", email="Alice@Example.com")

    assert store.count_users() == 1
    assert user.id
    assert user.username == "Alice"
    assert user.email == "Alice@Example.com"
    assert user.display_name == "Alice Analyst"
    assert user.role == "analyst"
    assert user.tenant_id == "tenant-a"
    assert user.password_hash == "hash-1"
    assert user.password_salt == "salt-1"
    assert user.must_change_password is False
    assert user.disabled is False
    assert user.created_at
    assert user.updated_at
    assert store.get_user(user.id) == user
    assert store.get_user_by_identifier("alice") == user
    assert store.get_user_by_identifier("ALICE@EXAMPLE.COM") == user


def test_create_user_rejects_duplicate_username_and_email_case_insensitively(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    _create_user(store, username="Alice", email="alice@example.com")

    with pytest.raises(ValueError, match="username"):
        _create_user(
            store,
            username="alice",
            email="alice2@example.com",
        )

    with pytest.raises(ValueError, match="email"):
        _create_user(
            store,
            username="alice2",
            email="ALICE@EXAMPLE.COM",
        )


def test_create_user_validates_role_and_normalizes_tenant_id(tmp_path):
    store = UserStore(tmp_path / "auth.db")

    user = _create_user(store, tenant_id=" tenant.a-1 ")

    assert user.tenant_id == "tenant.a-1"
    with pytest.raises(ValueError, match="role"):
        _create_user(store, username="bob", email="bob@example.com", role="owner")


def test_list_users_filters_by_tenant_when_scope_is_supplied(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    alice = _create_user(store, username="alice", email="alice@example.com", tenant_id="tenant-a")
    bob = _create_user(store, username="bob", email="bob@example.com", tenant_id="tenant-b")
    root = _create_user(store, username="root", email="root@example.com", tenant_id=None)

    assert store.list_users() == [alice, bob, root]
    assert store.list_users("tenant-a") == [alice]
    assert store.list_users("tenant-b") == [bob]


def test_update_user_changes_role_expiry_disabled_and_password_fields(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    user = _create_user(store)

    updated = store.update_user(
        user.id,
        role="admin",
        expires_at="2026-12-31T23:59:59+00:00",
        disabled=True,
        password_hash="hash-2",
        password_salt="salt-2",
        password_updated_at="2026-07-02T10:00:00+00:00",
        must_change_password=True,
    )

    assert updated.role == "admin"
    assert updated.expires_at == "2026-12-31T23:59:59+00:00"
    assert updated.disabled is True
    assert updated.password_hash == "hash-2"
    assert updated.password_salt == "salt-2"
    assert updated.password_updated_at == "2026-07-02T10:00:00+00:00"
    assert updated.must_change_password is True
    assert store.get_user(user.id) == updated


def test_delete_user_soft_deletes_user_and_removes_only_their_sessions(
    monkeypatch,
    tmp_path,
):
    store = UserStore(tmp_path / "auth.db")
    alice = _create_user(store, username="alice", email="alice@example.com")
    bob = _create_user(store, username="bob", email="bob@example.com")
    raw_ids = iter(["alice-one", "alice-two", "bob-one"])
    monkeypatch.setattr(
        user_store_module,
        "secrets",
        SimpleNamespace(token_urlsafe=lambda length: next(raw_ids)),
        raising=False,
    )
    alice_raw_one, _alice_session_one = store.create_session(alice.id)
    alice_raw_two, _alice_session_two = store.create_session(alice.id)
    bob_raw, bob_session = store.create_session(bob.id)
    deleted_at = datetime(2026, 7, 2, 12, 0, 0, tzinfo=timezone.utc)

    with monkeypatch.context() as clock:
        clock.setattr(user_store_module, "_utc_now_dt", lambda: deleted_at)
        deleted = store.delete_user(alice.id)

    assert deleted.id == alice.id
    assert deleted.disabled is True
    assert deleted.updated_at == deleted_at.isoformat()
    assert store.get_user(alice.id) == deleted
    assert store.get_user(bob.id) == bob
    assert store.get_session(alice_raw_one) is None
    assert store.get_session(alice_raw_two) is None
    assert store.get_session(bob_raw) == bob_session


def test_delete_user_raises_for_missing_user(tmp_path):
    store = UserStore(tmp_path / "auth.db")

    with pytest.raises(ValueError, match="user not found"):
        store.delete_user("missing-user")


def test_create_session_hashes_raw_session_id_and_rejects_expired_sessions(
    monkeypatch,
    tmp_path,
):
    store = UserStore(tmp_path / "auth.db")
    user = _create_user(store)
    raw_ids = iter(["raw-session-id", "expired-session-id"])

    def fake_token_urlsafe(length):
        assert length == 32
        return next(raw_ids)

    monkeypatch.setattr(
        user_store_module,
        "secrets",
        SimpleNamespace(token_urlsafe=fake_token_urlsafe),
        raising=False,
    )

    raw_session_id, session = store.create_session(user.id, ttl_seconds=60)

    assert raw_session_id == "raw-session-id"
    assert session.id_hash == hash_secret("raw-session-id")
    assert session.id_hash != raw_session_id
    assert session.user_id == user.id
    assert (
        _parse_timestamp(session.expires_at) - _parse_timestamp(session.created_at)
    ).total_seconds() == 60
    assert store.get_session("raw-session-id") == session
    assert store.get_session(session.id_hash) is None

    expired_raw_session_id, _expired_session = store.create_session(
        user.id,
        ttl_seconds=-1,
    )

    assert expired_raw_session_id == "expired-session-id"
    assert store.get_session("expired-session-id") is None


def test_delete_session_and_delete_sessions_for_user(monkeypatch, tmp_path):
    store = UserStore(tmp_path / "auth.db")
    alice = _create_user(store, username="alice", email="alice@example.com")
    bob = _create_user(store, username="bob", email="bob@example.com")
    raw_ids = iter(["alice-one", "alice-two", "bob-one"])
    monkeypatch.setattr(
        user_store_module,
        "secrets",
        SimpleNamespace(token_urlsafe=lambda length: next(raw_ids)),
        raising=False,
    )

    alice_raw_one, _alice_session_one = store.create_session(alice.id)
    alice_raw_two, _alice_session_two = store.create_session(alice.id)
    bob_raw, bob_session = store.create_session(bob.id)

    store.delete_session(alice_raw_one)

    assert store.get_session(alice_raw_one) is None
    assert store.get_session(alice_raw_two) is not None
    assert store.delete_sessions_for_user(alice.id) == 1
    assert store.get_session(alice_raw_two) is None
    assert store.get_session(bob_raw) == bob_session


def test_touch_session_updates_last_seen_and_optionally_extends_expiry(
    monkeypatch,
    tmp_path,
):
    store = UserStore(tmp_path / "auth.db")
    user = _create_user(store)
    monkeypatch.setattr(
        user_store_module,
        "secrets",
        SimpleNamespace(token_urlsafe=lambda length: "touch-session"),
        raising=False,
    )
    created_at = datetime(2026, 7, 2, 10, 0, 0, tzinfo=timezone.utc)
    touched_at = datetime(2026, 7, 2, 10, 0, 30, tzinfo=timezone.utc)

    with monkeypatch.context() as clock:
        clock.setattr(user_store_module, "_utc_now_dt", lambda: created_at)
        raw_session_id, session = store.create_session(user.id, ttl_seconds=60)

    with monkeypatch.context() as clock:
        clock.setattr(user_store_module, "_utc_now_dt", lambda: touched_at)
        touched = store.touch_session(raw_session_id, ttl_seconds=300)

    assert touched is not None
    assert touched.id_hash == hash_secret(raw_session_id)
    assert touched.id_hash != raw_session_id
    assert touched.user_id == session.user_id
    assert touched.created_at == session.created_at
    assert touched.last_seen_at == touched_at.isoformat()
    assert touched.expires_at == "2026-07-02T10:05:30+00:00"
    assert _parse_timestamp(touched.last_seen_at) > _parse_timestamp(session.last_seen_at)
    assert _parse_timestamp(touched.expires_at) > _parse_timestamp(session.expires_at)


def test_touch_session_returns_none_for_missing_or_expired_sessions(
    monkeypatch,
    tmp_path,
):
    store = UserStore(tmp_path / "auth.db")
    user = _create_user(store)
    monkeypatch.setattr(
        user_store_module,
        "secrets",
        SimpleNamespace(token_urlsafe=lambda length: "expired-session"),
        raising=False,
    )
    created_at = datetime(2026, 7, 2, 10, 0, 0, tzinfo=timezone.utc)
    after_expiry = datetime(2026, 7, 2, 10, 1, 1, tzinfo=timezone.utc)

    assert store.touch_session("missing-session") is None
    with monkeypatch.context() as clock:
        clock.setattr(user_store_module, "_utc_now_dt", lambda: created_at)
        raw_session_id, _session = store.create_session(user.id, ttl_seconds=60)

    with monkeypatch.context() as clock:
        clock.setattr(user_store_module, "_utc_now_dt", lambda: after_expiry)
        assert store.touch_session(raw_session_id) is None


def test_password_reset_tokens_track_attempts_used_at_and_expiry(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    user = _create_user(store)

    token = store.create_password_reset_token(
        user.id,
        "opaque-reset-code-hash",
        ttl_seconds=120,
    )

    assert token.id
    assert token.user_id == user.id
    assert token.code_hash == "opaque-reset-code-hash"
    assert token.used_at is None
    assert token.attempt_count == 0
    assert (
        _parse_timestamp(token.expires_at) - _parse_timestamp(token.created_at)
    ).total_seconds() == 120
    assert store.get_password_reset_token(token.id) == token

    attempted = store.increment_password_reset_attempts(token.id)
    assert attempted.attempt_count == 1
    used = store.mark_password_reset_token_used(token.id)
    assert used.used_at is not None
    assert used.attempt_count == 1

    expired = store.create_password_reset_token(
        user.id,
        "expired-opaque-reset-code-hash",
        ttl_seconds=-1,
    )
    assert store.get_password_reset_token(expired.id) is None


def test_delete_password_reset_token_removes_only_selected_token(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    user = _create_user(store)
    first = store.create_password_reset_token(user.id, "first-code-hash")
    second = store.create_password_reset_token(user.id, "second-code-hash")

    assert store.delete_password_reset_token(first.id) == 1

    assert store.get_password_reset_token(first.id) is None
    assert store.get_password_reset_token(second.id) == second
    assert store.delete_password_reset_token("missing-token") == 0


def test_get_web_auth_db_path_honors_override(monkeypatch, tmp_path):
    target = tmp_path / "custom-auth.db"
    monkeypatch.setenv("TRADINGAGENTS_WEB_AUTH_DB", str(target))

    assert web_state_module.get_web_auth_db_path() == target


def test_get_web_auth_db_path_defaults_to_web_state_base(monkeypatch, tmp_path):
    base = tmp_path / "web-state"
    monkeypatch.delenv("TRADINGAGENTS_WEB_AUTH_DB", raising=False)
    monkeypatch.setenv("TRADINGAGENTS_WEB_STATE_DIR", str(base))

    assert web_state_module.get_web_auth_db_path() == base / "auth.db"


def test_active_admin_count_is_scoped_and_excludes_disabled_or_expired_users(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    global_admin = _create_user(
        store,
        username="global-admin",
        email="global-admin@example.com",
        role="admin",
        tenant_id=None,
    )
    tenant_admin = _create_user(
        store,
        username="tenant-admin",
        email="tenant-admin@example.com",
        role="admin",
        tenant_id="tenant-a",
    )
    _create_user(
        store,
        username="disabled-admin",
        email="disabled-admin@example.com",
        role="admin",
        tenant_id="tenant-a",
        disabled=True,
    )
    _create_user(
        store,
        username="expired-admin",
        email="expired-admin@example.com",
        role="admin",
        tenant_id="tenant-a",
        expires_at="2000-01-01T00:00:00+00:00",
    )
    _create_user(
        store,
        username="viewer",
        email="viewer@example.com",
        role="viewer",
        tenant_id="tenant-a",
    )

    assert store.active_admin_count(None) == 1
    assert store.active_admin_count("tenant-a") == 1
    assert store.get_user(global_admin.id) is not None
    assert store.get_user(tenant_admin.id) is not None


def test_record_audit_event_persists_normalized_tenant_and_metadata(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    actor = _create_user(store, username="actor", email="actor@example.com")
    target = _create_user(store, username="target", email="target@example.com")

    event_id = store.record_audit_event(
        "user.disabled",
        actor_user_id=actor.id,
        target_user_id=target.id,
        tenant_id=" tenant-a ",
        metadata={"reason": "policy", "attempts": 2},
    )

    with sqlite3.connect(tmp_path / "auth.db") as conn:
        row = conn.execute(
            "SELECT * FROM audit_events WHERE id = ?",
            (event_id,),
        ).fetchone()

    assert row is not None
    assert row[1] == actor.id
    assert row[2] == target.id
    assert row[3] == "tenant-a"
    assert row[4] == "user.disabled"
    assert row[5]
    assert json.loads(row[6]) == {"attempts": 2, "reason": "policy"}


def test_bootstrap_admin_from_env_creates_first_admin(monkeypatch, tmp_path):
    store = UserStore(tmp_path / "auth.db")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_PASSWORD", "StrongAdmin123!")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_TENANT_ID", " tenant-a ")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_USERNAME", "root-admin")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_DISPLAY_NAME", "Root Admin")

    result = user_store_module.bootstrap_admin_from_env(store)

    assert result.created is True
    assert result.user_id
    assert result.reason is None
    user = store.get_user(result.user_id)
    assert user is not None
    assert user.username == "root-admin"
    assert user.email == "admin@example.com"
    assert user.display_name == "Root Admin"
    assert user.role == "admin"
    assert user.tenant_id == "tenant-a"
    assert user.must_change_password is True
    assert user.password_updated_at
    assert verify_password("StrongAdmin123!", user.password_hash, user.password_salt)


def test_bootstrap_admin_from_env_does_not_overwrite_existing_users(
    monkeypatch,
    tmp_path,
):
    store = UserStore(tmp_path / "auth.db")
    existing = _create_user(store)
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_PASSWORD", "StrongAdmin123!")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_TENANT_ID", "tenant-a")

    result = user_store_module.bootstrap_admin_from_env(store)

    assert result.created is False
    assert result.user_id is None
    assert result.reason == "users_exist"
    assert store.count_users() == 1
    assert store.get_user(existing.id) == existing
    assert store.get_user_by_identifier("admin@example.com") is None


def test_bootstrap_admin_from_env_skips_empty_store_when_required_env_missing(
    monkeypatch,
    tmp_path,
):
    store = UserStore(tmp_path / "auth.db")
    monkeypatch.delenv("TRADINGAGENTS_ADMIN_EMAIL", raising=False)
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_PASSWORD", "StrongAdmin123!")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_TENANT_ID", "tenant-a")

    result = user_store_module.bootstrap_admin_from_env(store)

    assert result.created is False
    assert result.user_id is None
    assert result.reason == "missing_env"
    assert store.count_users() == 0


def test_bootstrap_admin_from_env_validates_password_policy(monkeypatch, tmp_path):
    store = UserStore(tmp_path / "auth.db")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_PASSWORD", "short")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_TENANT_ID", "tenant-a")

    with pytest.raises(ValueError, match="at least 10 characters"):
        user_store_module.bootstrap_admin_from_env(store)

    assert store.count_users() == 0
