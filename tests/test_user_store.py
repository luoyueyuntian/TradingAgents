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
    "tenants": [
        "id",
        "tenant_id",
        "display_name",
        "disabled",
        "archived",
        "created_at",
        "updated_at",
    ],
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


def _table_info_by_column(db_path, table_name):
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1]: row for row in rows}


def _ensure_tenant(store, tenant_id, display_name=None):
    if tenant_id is None:
        return None
    try:
        normalized_tenant_id = web_state_module.normalize_web_tenant_id(tenant_id)
    except ValueError:
        return None
    tenant = store.get_tenant(normalized_tenant_id)
    if tenant is None:
        tenant = store.create_tenant(
            normalized_tenant_id,
            display_name=display_name or normalized_tenant_id,
        )
    return tenant


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
    _ensure_tenant(store, values["tenant_id"])
    return store.create_user(**values)


def _insert_user_direct(db_path, **overrides):
    values = {
        "id": "direct-user",
        "username": "direct-user",
        "email": "direct@example.com",
        "display_name": "Direct User",
        "role": "analyst",
        "tenant_id": "tenant-a",
        "password_hash": "hash-direct",
        "password_salt": "salt-direct",
        "password_updated_at": None,
        "must_change_password": 0,
        "expires_at": None,
        "disabled": 0,
        "created_at": "2026-07-02T10:00:00+00:00",
        "updated_at": "2026-07-02T10:00:00+00:00",
        "last_login_at": None,
    }
    values.update(overrides)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO users (
                id,
                username,
                email,
                display_name,
                role,
                tenant_id,
                password_hash,
                password_salt,
                password_updated_at,
                must_change_password,
                expires_at,
                disabled,
                created_at,
                updated_at,
                last_login_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            tuple(values.values()),
        )


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
    assert _table_info_by_column(db_path, "users")["tenant_id"][3] == 1


def test_ensure_schema_creates_tenants_table(tmp_path):
    db_path = tmp_path / "auth.db"

    UserStore(db_path).ensure_schema()

    assert _table_columns(db_path, "tenants") == EXPECTED_SCHEMA["tenants"]
    tenant_info = _table_info_by_column(db_path, "tenants")
    assert tenant_info["tenant_id"][3] == 1
    assert tenant_info["display_name"][3] == 1
    assert tenant_info["disabled"][4] == "0"
    assert tenant_info["archived"][4] == "0"


def test_ensure_schema_backfills_tenants_from_existing_user_rows(tmp_path):
    db_path = tmp_path / "auth.db"
    store = UserStore(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                role TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                password_updated_at TEXT,
                must_change_password INTEGER NOT NULL DEFAULT 1,
                expires_at TEXT,
                disabled INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_login_at TEXT
            )
            """
        )
    _insert_user_direct(
        db_path,
        id="user-a",
        username="user-a",
        email="user-a@example.com",
        tenant_id="tenant-a",
    )
    _insert_user_direct(
        db_path,
        id="user-b",
        username="user-b",
        email="user-b@example.com",
        tenant_id="tenant-b",
    )
    _insert_user_direct(
        db_path,
        id="user-c",
        username="user-c",
        email="user-c@example.com",
        tenant_id="tenant-a",
    )

    store.ensure_schema()

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT tenant_id, display_name, disabled, archived
            FROM tenants
            ORDER BY tenant_id
            """
        ).fetchall()

    assert rows == [
        ("tenant-a", "tenant-a", 0, 0),
        ("tenant-b", "tenant-b", 0, 0),
    ]


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


def test_sqlite_rejects_direct_case_insensitive_username_and_email_duplicates(tmp_path):
    db_path = tmp_path / "auth.db"
    store = UserStore(db_path)
    _create_user(store, username="Alice", email="Alice@Example.com")

    with pytest.raises(sqlite3.IntegrityError):
        _insert_user_direct(
            db_path,
            id="duplicate-username",
            username="alice",
            email="alice2@example.com",
        )

    with pytest.raises(sqlite3.IntegrityError):
        _insert_user_direct(
            db_path,
            id="duplicate-email",
            username="alice2",
            email="ALICE@example.com",
        )


def test_create_user_validates_role_and_normalizes_tenant_id(tmp_path):
    store = UserStore(tmp_path / "auth.db")

    user = _create_user(store, tenant_id=" tenant.a-1 ")

    assert user.tenant_id == "tenant.a-1"
    with pytest.raises(ValueError, match="role"):
        _create_user(store, username="bob", email="bob@example.com", role="owner")
    with pytest.raises(ValueError, match="tenant_id"):
        _create_user(
            store,
            username="no-tenant",
            email="no-tenant@example.com",
            tenant_id=None,
        )
    with pytest.raises(ValueError, match="tenant_id"):
        _create_user(
            store,
            username="blank-tenant",
            email="blank-tenant@example.com",
            tenant_id=" ",
        )
    with pytest.raises(ValueError, match="tenant_id"):
        _create_user(
            store,
            username="bad-tenant",
            email="bad-tenant@example.com",
            tenant_id="../escape",
        )
    with pytest.raises(ValueError, match="tenant_id"):
        store.update_user(user.id, tenant_id=None)
    with pytest.raises(ValueError, match="tenant_id"):
        store.update_user(user.id, tenant_id=" ")
    with pytest.raises(ValueError, match="tenant_id"):
        store.update_user(user.id, tenant_id="../escape")


def test_list_users_filters_by_tenant_when_scope_is_supplied(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    alice = _create_user(store, username="alice", email="alice@example.com", tenant_id="tenant-a")
    bob = _create_user(store, username="bob", email="bob@example.com", tenant_id="tenant-b")
    carol = _create_user(store, username="carol", email="carol@example.com", tenant_id="tenant-c")

    assert store.list_users() == [alice, bob, carol]
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


def test_create_and_update_user_reject_malformed_or_naive_expiry(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    user = _create_user(store)

    with pytest.raises(ValueError, match="expires_at"):
        _create_user(
            store,
            username="bad-expiry",
            email="bad-expiry@example.com",
            expires_at="not-a-timestamp",
        )
    with pytest.raises(ValueError, match="expires_at"):
        _create_user(
            store,
            username="naive-expiry",
            email="naive-expiry@example.com",
            expires_at="2026-07-02T10:00:00",
        )
    with pytest.raises(ValueError, match="expires_at"):
        store.update_user(user.id, expires_at="not-a-timestamp")
    with pytest.raises(ValueError, match="expires_at"):
        store.update_user(user.id, expires_at="2026-07-02T10:00:00")


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


def test_create_session_rejects_disabled_or_expired_users(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    disabled = _create_user(
        store,
        username="disabled",
        email="disabled@example.com",
        disabled=True,
    )
    expired = _create_user(
        store,
        username="expired",
        email="expired@example.com",
        expires_at="2000-01-01T00:00:00+00:00",
    )

    with pytest.raises(ValueError, match="user not active"):
        store.create_session(disabled.id)
    with pytest.raises(ValueError, match="user not active"):
        store.create_session(expired.id)


def test_get_and_touch_session_return_none_when_linked_user_disabled_or_expired(
    monkeypatch,
    tmp_path,
):
    db_path = tmp_path / "auth.db"
    store = UserStore(db_path)
    disabled_user = _create_user(
        store,
        username="disabled",
        email="disabled@example.com",
    )
    expired_user = _create_user(
        store,
        username="expired",
        email="expired@example.com",
    )
    raw_ids = iter(["disabled-session", "expired-session"])
    monkeypatch.setattr(
        user_store_module,
        "secrets",
        SimpleNamespace(token_urlsafe=lambda length: next(raw_ids)),
        raising=False,
    )
    disabled_raw_session_id, _disabled_session = store.create_session(disabled_user.id)
    expired_raw_session_id, _expired_session = store.create_session(expired_user.id)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE users SET disabled = 1 WHERE id = ?", (disabled_user.id,))
        conn.execute(
            "UPDATE users SET expires_at = ? WHERE id = ?",
            ("2000-01-01T00:00:00+00:00", expired_user.id),
        )

    assert store.get_session(disabled_raw_session_id) is None
    assert store.touch_session(disabled_raw_session_id) is None
    assert store.get_session(expired_raw_session_id) is None
    assert store.touch_session(expired_raw_session_id) is None


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


def test_update_user_disabled_invalidates_sessions(monkeypatch, tmp_path):
    store = UserStore(tmp_path / "auth.db")
    user = _create_user(store)
    monkeypatch.setattr(
        user_store_module,
        "secrets",
        SimpleNamespace(token_urlsafe=lambda length: "disabled-user-session"),
        raising=False,
    )
    raw_session_id, _session = store.create_session(user.id)

    updated = store.update_user(user.id, disabled=True)

    assert updated.disabled is True
    assert store.get_session(raw_session_id) is None


def test_update_user_and_delete_sessions_updates_password_and_invalidates_sessions(
    monkeypatch,
    tmp_path,
):
    store = UserStore(tmp_path / "auth.db")
    user = _create_user(
        store,
        password_hash="old-hash",
        password_salt="old-salt",
        must_change_password=False,
    )
    monkeypatch.setattr(
        user_store_module,
        "secrets",
        SimpleNamespace(token_urlsafe=lambda length: "password-reset-session"),
        raising=False,
    )
    raw_session_id, _session = store.create_session(user.id)

    updated = store.update_user_and_delete_sessions(
        user.id,
        password_hash="new-hash",
        password_salt="new-salt",
        password_updated_at="2026-07-02T10:00:00+00:00",
        must_change_password=True,
    )

    assert updated.password_hash == "new-hash"
    assert updated.password_salt == "new-salt"
    assert updated.password_updated_at == "2026-07-02T10:00:00+00:00"
    assert updated.must_change_password is True
    assert store.get_session(raw_session_id) is None


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


def test_create_password_reset_token_rejects_disabled_or_expired_users(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    disabled = _create_user(
        store,
        username="disabled",
        email="disabled@example.com",
        disabled=True,
    )
    expired = _create_user(
        store,
        username="expired",
        email="expired@example.com",
        expires_at="2000-01-01T00:00:00+00:00",
    )

    with pytest.raises(ValueError, match="user not active"):
        store.create_password_reset_token(disabled.id, "disabled-code-hash")
    with pytest.raises(ValueError, match="user not active"):
        store.create_password_reset_token(expired.id, "expired-code-hash")


def test_password_reset_token_becomes_unusable_when_user_is_disabled_or_expired(
    tmp_path,
):
    db_path = tmp_path / "auth.db"
    store = UserStore(db_path)
    disabled_user = _create_user(
        store,
        username="disabled",
        email="disabled@example.com",
    )
    expired_user = _create_user(
        store,
        username="expired",
        email="expired@example.com",
    )
    disabled_token = store.create_password_reset_token(
        disabled_user.id,
        "disabled-later-code-hash",
    )
    expired_token = store.create_password_reset_token(
        expired_user.id,
        "expired-later-code-hash",
    )

    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE users SET disabled = 1 WHERE id = ?", (disabled_user.id,))
        conn.execute(
            "UPDATE users SET expires_at = ? WHERE id = ?",
            ("2000-01-01T00:00:00+00:00", expired_user.id),
        )

    assert store.get_password_reset_token(disabled_token.id) is None
    assert store.get_password_reset_token(expired_token.id) is None
    with pytest.raises(ValueError, match="user not active"):
        store.increment_password_reset_attempts(disabled_token.id)
    with pytest.raises(ValueError, match="user not active"):
        store.increment_password_reset_attempts(expired_token.id)
    with pytest.raises(ValueError, match="user not active"):
        store.mark_password_reset_token_used(disabled_token.id)
    with pytest.raises(ValueError, match="user not active"):
        store.mark_password_reset_token_used(expired_token.id)


def test_used_password_reset_token_is_not_publicly_retrievable_or_reusable(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    user = _create_user(store)
    token = store.create_password_reset_token(user.id, "one-use-code-hash")

    used = store.mark_password_reset_token_used(token.id)

    assert used.used_at is not None
    assert store.get_password_reset_token(token.id) is None
    with pytest.raises(ValueError, match="password reset token"):
        store.mark_password_reset_token_used(token.id)


def test_password_reset_attempts_allow_limit_then_block_next_attempt(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    user = _create_user(store)
    token = store.create_password_reset_token(user.id, "attempt-limit-code-hash")

    max_attempts = user_store_module.PASSWORD_RESET_MAX_ATTEMPTS
    for expected_attempts in range(1, max_attempts + 1):
        attempted = store.increment_password_reset_attempts(token.id)
        assert attempted.attempt_count == expected_attempts

    with pytest.raises(ValueError, match="too many"):
        store.increment_password_reset_attempts(token.id)
    with pytest.raises(ValueError, match="too many"):
        store.mark_password_reset_token_used(token.id)
    assert store.get_password_reset_token(token.id).attempt_count == max_attempts


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
    tenant_b_admin = _create_user(
        store,
        username="tenant-b-admin",
        email="tenant-b-admin@example.com",
        role="admin",
        tenant_id="tenant-b",
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

    assert store.active_admin_count(None) == 2
    assert store.active_admin_count("tenant-a") == 1
    assert store.get_user(tenant_b_admin.id) is not None
    assert store.get_user(tenant_admin.id) is not None


@pytest.mark.parametrize(
    ("updates", "expected_message"),
    [
        ({"disabled": True}, "Cannot remove the last active admin from tenant"),
        ({"role": "viewer"}, "Cannot remove the last active admin from tenant"),
        ({"expires_at": "2000-01-01T00:00:00+00:00"}, "Cannot remove the last active admin from tenant"),
    ],
)
def test_update_user_transactionally_protects_last_active_admin(tmp_path, updates, expected_message):
    store = UserStore(tmp_path / "auth.db")
    sole_admin = _create_user(
        store,
        username="sole-admin",
        email="sole-admin@example.com",
        role="admin",
        tenant_id="tenant-a",
    )

    with pytest.raises(ValueError, match=expected_message):
        store.update_user(sole_admin.id, **updates)

    refreshed = store.get_user(sole_admin.id)
    assert refreshed is not None
    assert refreshed.role == "admin"
    assert refreshed.disabled is False
    assert refreshed.expires_at is None


def test_delete_user_transactionally_protects_last_active_admin(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    sole_admin = _create_user(
        store,
        username="sole-admin",
        email="sole-admin@example.com",
        role="admin",
        tenant_id="tenant-a",
    )

    with pytest.raises(ValueError, match="Cannot remove the last active admin from tenant"):
        store.delete_user(sole_admin.id)

    refreshed = store.get_user(sole_admin.id)
    assert refreshed is not None
    assert refreshed.disabled is False


@pytest.mark.parametrize("tenant_updates", [{"disabled": True}, {"archived": True}])
def test_update_user_allows_last_admin_cleanup_when_tenant_is_unavailable(tmp_path, tenant_updates):
    store = UserStore(tmp_path / "auth.db")
    _create_user(
        store,
        username="other-admin",
        email="other-admin@example.com",
        role="admin",
        tenant_id="tenant-b",
    )
    sole_admin = _create_user(
        store,
        username="sole-admin",
        email="sole-admin@example.com",
        role="admin",
        tenant_id="tenant-a",
    )
    store.update_tenant("tenant-a", **tenant_updates)

    updated = store.update_user(sole_admin.id, role="viewer")

    assert updated.role == "viewer"
    refreshed = store.get_user(sole_admin.id)
    assert refreshed is not None
    assert refreshed.role == "viewer"


@pytest.mark.parametrize("tenant_updates", [{"disabled": True}, {"archived": True}])
def test_delete_user_allows_last_admin_cleanup_when_tenant_is_unavailable(tmp_path, tenant_updates):
    store = UserStore(tmp_path / "auth.db")
    _create_user(
        store,
        username="other-admin",
        email="other-admin@example.com",
        role="admin",
        tenant_id="tenant-b",
    )
    sole_admin = _create_user(
        store,
        username="sole-admin",
        email="sole-admin@example.com",
        role="admin",
        tenant_id="tenant-a",
    )
    store.update_tenant("tenant-a", **tenant_updates)

    deleted = store.delete_user(sole_admin.id)

    assert deleted.disabled is True
    refreshed = store.get_user(sole_admin.id)
    assert refreshed is not None
    assert refreshed.disabled is True


def test_archive_tenant_lifecycle_create_update_and_list(tmp_path):
    store = UserStore(tmp_path / "auth.db")

    created = store.create_tenant(" tenant-a ", display_name=" Tenant A ")

    assert created.tenant_id == "tenant-a"
    assert created.display_name == "Tenant A"
    assert created.disabled is False
    assert created.archived is False
    assert store.get_tenant("tenant-a") == created
    assert store.list_tenants() == [created]

    updated = store.update_tenant(
        "tenant-a",
        display_name="Tenant Alpha",
        disabled=True,
        archived=True,
    )

    assert updated.tenant_id == "tenant-a"
    assert updated.display_name == "Tenant Alpha"
    assert updated.disabled is True
    assert updated.archived is True
    assert store.get_tenant(" tenant-a ") == updated
    assert store.list_tenants() == []
    assert store.list_tenants(include_archived=True) == [updated]

    with pytest.raises(ValueError, match="display_name"):
        store.create_tenant("tenant-b", display_name=" ")
    with pytest.raises(ValueError, match="display_name"):
        store.update_tenant("tenant-a", display_name=" ")
    with pytest.raises(ValueError, match="tenant_id"):
        store.create_tenant("../escape", display_name="Nope")
    with pytest.raises(ValueError, match="disabled"):
        store.update_tenant("tenant-a", disabled=2)
    with pytest.raises(ValueError, match="archived"):
        store.update_tenant("tenant-a", archived=-1)
    with pytest.raises(ValueError, match="no fields to update"):
        store.update_tenant("tenant-a")
    with pytest.raises(ValueError, match="tenant not found"):
        store.update_tenant("missing-tenant", display_name="Missing")


def test_list_tenants_sorts_by_tenant_id_and_hides_archived_by_default(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    store.create_tenant("tenant-b", display_name="Tenant B")
    store.create_tenant("tenant-a", display_name="Tenant A")
    store.create_tenant("tenant-c", display_name="Tenant C")
    store.update_tenant("tenant-b", archived=True)

    assert [tenant.tenant_id for tenant in store.list_tenants()] == [
        "tenant-a",
        "tenant-c",
    ]
    assert [tenant.tenant_id for tenant in store.list_tenants(include_archived=True)] == [
        "tenant-a",
        "tenant-b",
        "tenant-c",
    ]


def test_update_tenant_transactionally_rejects_non_unarchive_writes_for_archived_tenant(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    store.create_tenant("tenant-a", display_name="Tenant A")
    store.update_tenant("tenant-a", archived=True)

    with pytest.raises(ValueError, match="Archived tenants are read-only"):
        store.update_tenant("tenant-a", disabled=True)

    with pytest.raises(ValueError, match="Archived tenants are read-only"):
        store.update_tenant("tenant-a", display_name="Tenant Alpha")

    archived = store.get_tenant("tenant-a")
    assert archived is not None
    assert archived.display_name == "Tenant A"
    assert archived.disabled is False
    assert archived.archived is True

    unarchived = store.update_tenant("tenant-a", archived=False)
    assert unarchived.archived is False


def test_update_tenant_transactionally_protects_last_login_capable_admin_tenant(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    _create_user(
        store,
        username="tenant-a-admin",
        email="tenant-a-admin@example.com",
        role="admin",
        tenant_id="tenant-a",
        must_change_password=False,
    )
    _create_user(
        store,
        username="tenant-b-admin",
        email="tenant-b-admin@example.com",
        role="admin",
        tenant_id="tenant-b",
        must_change_password=False,
    )
    store.update_tenant("tenant-a", disabled=True)

    with pytest.raises(ValueError, match="Cannot disable or archive the last tenant with a login-capable admin"):
        store.update_tenant("tenant-b", archived=True)

    tenant_b = store.get_tenant("tenant-b")
    assert tenant_b is not None
    assert tenant_b.disabled is False
    assert tenant_b.archived is False


def test_tenant_user_counts_are_scoped_to_target_tenant(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    store.create_tenant("tenant-a", display_name="Tenant A")
    store.create_tenant("tenant-b", display_name="Tenant B")
    _create_user(
        store,
        username="tenant-a-admin",
        email="tenant-a-admin@example.com",
        role="admin",
        tenant_id="tenant-a",
    )
    _create_user(
        store,
        username="tenant-a-analyst",
        email="tenant-a-analyst@example.com",
        role="analyst",
        tenant_id="tenant-a",
    )
    _create_user(
        store,
        username="tenant-a-disabled-admin",
        email="tenant-a-disabled-admin@example.com",
        role="admin",
        tenant_id="tenant-a",
        disabled=True,
    )
    _create_user(
        store,
        username="tenant-a-expired-admin",
        email="tenant-a-expired-admin@example.com",
        role="admin",
        tenant_id="tenant-a",
        expires_at="2000-01-01T00:00:00+00:00",
    )
    _create_user(
        store,
        username="tenant-b-admin",
        email="tenant-b-admin@example.com",
        role="admin",
        tenant_id="tenant-b",
    )

    assert store.get_tenant_stats("tenant-a") == {
        "user_count": 4,
        "active_admin_count": 1,
    }
    assert store.get_tenant_stats(" tenant-b ") == {
        "user_count": 1,
        "active_admin_count": 1,
    }


def test_user_writes_reject_unknown_tenants_and_do_not_create_registry_rows(tmp_path):
    store = UserStore(tmp_path / "auth.db")
    _ensure_tenant(store, "tenant-a")

    with pytest.raises(ValueError, match="tenant not found"):
        store.create_user(
            username="unknown-tenant-user",
            email="unknown-tenant-user@example.com",
            display_name="Unknown Tenant User",
            role="analyst",
            tenant_id="tenant-missing",
            password_hash="hash-missing",
            password_salt="salt-missing",
            must_change_password=False,
        )
    assert store.get_tenant("tenant-missing") is None

    user = _create_user(store, tenant_id="tenant-a")

    with pytest.raises(ValueError, match="tenant not found"):
        store.update_user(user.id, tenant_id="tenant-other")
    assert store.get_tenant("tenant-other") is None


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


@pytest.mark.parametrize(
    ("tenant_update", "expected_reason"),
    [
        ({"disabled": True}, "tenant_disabled"),
        ({"archived": True}, "tenant_archived"),
    ],
)
def test_bootstrap_admin_from_env_rejects_unavailable_existing_tenants(
    monkeypatch,
    tmp_path,
    tenant_update,
    expected_reason,
):
    store = UserStore(tmp_path / "auth.db")
    store.create_tenant("tenant-a", display_name="Tenant A")
    store.update_tenant("tenant-a", **tenant_update)
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_PASSWORD", "StrongAdmin123!")
    monkeypatch.setenv("TRADINGAGENTS_ADMIN_TENANT_ID", "tenant-a")

    result = user_store_module.bootstrap_admin_from_env(store)

    assert result.created is False
    assert result.user_id is None
    assert result.reason == expected_reason
    assert store.count_users() == 0
    assert store.get_user_by_identifier("admin@example.com") is None
