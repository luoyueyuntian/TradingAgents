"""SQLite-backed user store for TradingAgents Web authentication."""

from __future__ import annotations

import json
import os
import secrets
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from tradingagents.service.web_state import normalize_web_tenant_id
from web.passwords import hash_password, hash_secret, validate_password_policy

VALID_ROLES = {"admin", "analyst", "viewer"}


@dataclass(frozen=True)
class UserRecord:
    id: str
    username: str
    email: str
    display_name: str
    role: str
    tenant_id: str | None
    password_hash: str
    password_salt: str
    password_updated_at: str | None
    must_change_password: bool
    expires_at: str | None
    disabled: bool
    created_at: str
    updated_at: str
    last_login_at: str | None


@dataclass(frozen=True)
class SessionRecord:
    id_hash: str
    user_id: str
    created_at: str
    last_seen_at: str
    expires_at: str


@dataclass(frozen=True)
class PasswordResetTokenRecord:
    id: str
    user_id: str
    code_hash: str
    created_at: str
    expires_at: str
    used_at: str | None
    attempt_count: int


@dataclass(frozen=True)
class BootstrapResult:
    created: bool
    user_id: str | None = None
    reason: str | None = None


def _utc_now() -> str:
    return _utc_now_dt().isoformat()


def _utc_now_dt() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _format_timestamp(value: datetime) -> str:
    return value.isoformat()


def _is_expired(expires_at: str) -> bool:
    return datetime.fromisoformat(expires_at) <= _utc_now_dt()


def _validate_optional_expires_at(expires_at: str | None) -> str | None:
    if expires_at is None:
        return None
    try:
        parsed = datetime.fromisoformat(expires_at)
    except ValueError as exc:
        raise ValueError("expires_at must be an offset-aware ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("expires_at must be an offset-aware ISO timestamp")
    return expires_at


def _require_text(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be blank")
    return normalized


def _validate_role(role: str) -> str:
    normalized = role.strip()
    if normalized not in VALID_ROLES:
        raise ValueError("role must be one of admin, analyst, or viewer")
    return normalized


def _normalize_tenant_id(tenant_id: str | None) -> str | None:
    if tenant_id is None:
        return None
    return normalize_web_tenant_id(tenant_id)


def _user_from_row(row: sqlite3.Row) -> UserRecord:
    return UserRecord(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        display_name=row["display_name"],
        role=row["role"],
        tenant_id=row["tenant_id"],
        password_hash=row["password_hash"],
        password_salt=row["password_salt"],
        password_updated_at=row["password_updated_at"],
        must_change_password=bool(row["must_change_password"]),
        expires_at=row["expires_at"],
        disabled=bool(row["disabled"]),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        last_login_at=row["last_login_at"],
    )


def _session_from_row(row: sqlite3.Row) -> SessionRecord:
    return SessionRecord(
        id_hash=row["id_hash"],
        user_id=row["user_id"],
        created_at=row["created_at"],
        last_seen_at=row["last_seen_at"],
        expires_at=row["expires_at"],
    )


def _password_reset_token_from_row(row: sqlite3.Row) -> PasswordResetTokenRecord:
    return PasswordResetTokenRecord(
        id=row["id"],
        user_id=row["user_id"],
        code_hash=row["code_hash"],
        created_at=row["created_at"],
        expires_at=row["expires_at"],
        used_at=row["used_at"],
        attempt_count=int(row["attempt_count"]),
    )


def _user_row_is_active(row: sqlite3.Row) -> bool:
    if bool(row["disabled"]):
        return False
    expires_at = row["expires_at"]
    return expires_at is None or not _is_expired(expires_at)


class UserStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    email TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    tenant_id TEXT,
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
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id_hash TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    code_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used_at TEXT,
                    attempt_count INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS audit_events (
                    id TEXT PRIMARY KEY,
                    actor_user_id TEXT,
                    target_user_id TEXT,
                    tenant_id TEXT,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    metadata TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS users_username_ci_unique
                ON users(lower(username))
                """
            )
            conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS users_email_ci_unique
                ON users(lower(email))
                """
            )

    def count_users(self) -> int:
        self.ensure_schema()
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()
        return int(row["count"])

    def create_user(
        self,
        *,
        username: str,
        email: str,
        display_name: str,
        role: str,
        tenant_id: str | None,
        password_hash: str,
        password_salt: str,
        password_updated_at: str | None = None,
        must_change_password: bool = True,
        expires_at: str | None = None,
        disabled: bool = False,
        last_login_at: str | None = None,
        user_id: str | None = None,
    ) -> UserRecord:
        self.ensure_schema()
        normalized_username = _require_text(username, "username")
        normalized_email = _require_text(email, "email")
        normalized_display_name = _require_text(display_name, "display_name")
        normalized_role = _validate_role(role)
        normalized_tenant_id = _normalize_tenant_id(tenant_id)
        normalized_password_hash = _require_text(password_hash, "password_hash")
        normalized_password_salt = _require_text(password_salt, "password_salt")
        normalized_expires_at = _validate_optional_expires_at(expires_at)
        now = _utc_now()
        resolved_user_id = user_id or uuid.uuid4().hex

        with self._connect() as conn:
            self._raise_for_duplicate_user_field(
                conn,
                "username",
                normalized_username,
            )
            self._raise_for_duplicate_user_field(conn, "email", normalized_email)
            try:
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
                    (
                        resolved_user_id,
                        normalized_username,
                        normalized_email,
                        normalized_display_name,
                        normalized_role,
                        normalized_tenant_id,
                        normalized_password_hash,
                        normalized_password_salt,
                        password_updated_at,
                        int(must_change_password),
                        normalized_expires_at,
                        int(disabled),
                        now,
                        now,
                        last_login_at,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ValueError("username or email already exists") from exc
            return self._get_user_by_id(conn, resolved_user_id)

    def get_user(self, user_id: str) -> UserRecord | None:
        self.ensure_schema()
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _user_from_row(row) if row is not None else None

    def get_user_by_identifier(self, identifier: str) -> UserRecord | None:
        self.ensure_schema()
        normalized = identifier.strip().casefold()
        if not normalized:
            return None
        with self._connect() as conn:
            for row in conn.execute("SELECT * FROM users ORDER BY rowid").fetchall():
                if row["username"].casefold() == normalized:
                    return _user_from_row(row)
                if row["email"].casefold() == normalized:
                    return _user_from_row(row)
        return None

    def list_users(self, tenant_id: str | None = None) -> list[UserRecord]:
        self.ensure_schema()
        normalized_tenant_id = _normalize_tenant_id(tenant_id)
        with self._connect() as conn:
            if normalized_tenant_id is None:
                rows = conn.execute("SELECT * FROM users ORDER BY rowid").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM users WHERE tenant_id = ? ORDER BY rowid",
                    (normalized_tenant_id,),
                ).fetchall()
        return [_user_from_row(row) for row in rows]

    def update_user(self, user_id: str, **fields: Any) -> UserRecord:
        self.ensure_schema()
        allowed_fields = {
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
            "last_login_at",
        }
        unknown_fields = sorted(set(fields) - allowed_fields)
        if unknown_fields:
            raise ValueError(f"unsupported user field: {unknown_fields[0]}")

        with self._connect() as conn:
            current = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if current is None:
                raise ValueError("user not found")

            updates: dict[str, Any] = {}
            for field_name, value in fields.items():
                if field_name in {"username", "email", "display_name"}:
                    value = _require_text(value, field_name)
                elif field_name == "role":
                    value = _validate_role(value)
                elif field_name == "tenant_id":
                    value = _normalize_tenant_id(value)
                elif field_name == "expires_at":
                    value = _validate_optional_expires_at(value)
                elif field_name in {"password_hash", "password_salt"}:
                    value = _require_text(value, field_name)
                elif field_name in {"must_change_password", "disabled"}:
                    value = int(value)
                updates[field_name] = value

            if "username" in updates:
                self._raise_for_duplicate_user_field(
                    conn,
                    "username",
                    updates["username"],
                    excluding_user_id=user_id,
                )
            if "email" in updates:
                self._raise_for_duplicate_user_field(
                    conn,
                    "email",
                    updates["email"],
                    excluding_user_id=user_id,
                )

            if updates:
                updates["updated_at"] = _utc_now()
                assignments = ", ".join(f"{field_name} = ?" for field_name in updates)
                conn.execute(
                    f"UPDATE users SET {assignments} WHERE id = ?",
                    (*updates.values(), user_id),
                )
                if updates.get("disabled") == 1:
                    conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            return self._get_user_by_id(conn, user_id)

    def delete_user(self, user_id: str) -> UserRecord:
        self.ensure_schema()
        with self._connect() as conn:
            self._get_user_by_id(conn, user_id)
            conn.execute(
                """
                UPDATE users
                SET disabled = 1,
                    updated_at = ?
                WHERE id = ?
                """,
                (_utc_now(), user_id),
            )
            conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            return self._get_user_by_id(conn, user_id)

    def _get_user_by_id(self, conn: sqlite3.Connection, user_id: str) -> UserRecord:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        if row is None:
            raise ValueError("user not found")
        return _user_from_row(row)

    def _raise_for_duplicate_user_field(
        self,
        conn: sqlite3.Connection,
        field_name: str,
        value: str,
        *,
        excluding_user_id: str | None = None,
    ) -> None:
        normalized = value.casefold()
        for row in conn.execute(f"SELECT id, {field_name} FROM users").fetchall():
            if excluding_user_id is not None and row["id"] == excluding_user_id:
                continue
            if row[field_name].casefold() == normalized:
                raise ValueError(f"{field_name} already exists")

    def active_admin_count(self, tenant_id: str | None) -> int:
        self.ensure_schema()
        normalized_tenant_id = _normalize_tenant_id(tenant_id)
        with self._connect() as conn:
            if normalized_tenant_id is None:
                rows = conn.execute(
                    """
                    SELECT * FROM users
                    WHERE role = 'admin'
                      AND disabled = 0
                      AND tenant_id IS NULL
                    """
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM users
                    WHERE role = 'admin'
                      AND disabled = 0
                      AND tenant_id = ?
                    """,
                    (normalized_tenant_id,),
                ).fetchall()
        return sum(
            1
            for row in rows
            if row["expires_at"] is None or not _is_expired(row["expires_at"])
        )

    def record_audit_event(
        self,
        event_type: str,
        *,
        actor_user_id: str | None = None,
        target_user_id: str | None = None,
        tenant_id: str | None = None,
        metadata: Any = None,
    ) -> str:
        self.ensure_schema()
        event_id = uuid.uuid4().hex
        normalized_event_type = _require_text(event_type, "event_type")
        normalized_tenant_id = _normalize_tenant_id(tenant_id)
        encoded_metadata = (
            json.dumps(metadata, sort_keys=True) if metadata is not None else None
        )
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_events (
                    id,
                    actor_user_id,
                    target_user_id,
                    tenant_id,
                    event_type,
                    created_at,
                    metadata
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    actor_user_id,
                    target_user_id,
                    normalized_tenant_id,
                    normalized_event_type,
                    _utc_now(),
                    encoded_metadata,
                ),
            )
        return event_id

    def create_session(
        self,
        user_id: str,
        *,
        ttl_seconds: int = 43_200,
    ) -> tuple[str, SessionRecord]:
        self.ensure_schema()
        raw_session_id = secrets.token_urlsafe(32)
        id_hash = hash_secret(raw_session_id)
        created_at = _utc_now_dt()
        expires_at = created_at + timedelta(seconds=ttl_seconds)

        with self._connect() as conn:
            user = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if user is None:
                raise ValueError("user not found")
            if not _user_row_is_active(user):
                raise ValueError("user not active")
            conn.execute(
                """
                INSERT INTO sessions (
                    id_hash,
                    user_id,
                    created_at,
                    last_seen_at,
                    expires_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    id_hash,
                    user_id,
                    _format_timestamp(created_at),
                    _format_timestamp(created_at),
                    _format_timestamp(expires_at),
                ),
            )
            row = conn.execute(
                "SELECT * FROM sessions WHERE id_hash = ?",
                (id_hash,),
            ).fetchone()
        return raw_session_id, _session_from_row(row)

    def get_session(self, raw_session_id: str) -> SessionRecord | None:
        self.ensure_schema()
        id_hash = hash_secret(raw_session_id)
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id_hash = ?",
                (id_hash,),
            ).fetchone()
            if row is None or _is_expired(row["expires_at"]):
                return None
            user = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (row["user_id"],),
            ).fetchone()
            if user is None or not _user_row_is_active(user):
                return None
            return _session_from_row(row)

    def touch_session(
        self,
        raw_session_id: str,
        *,
        ttl_seconds: int | None = None,
    ) -> SessionRecord | None:
        self.ensure_schema()
        id_hash = hash_secret(raw_session_id)
        now = _utc_now_dt()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id_hash = ?",
                (id_hash,),
            ).fetchone()
            if row is None or datetime.fromisoformat(row["expires_at"]) <= now:
                return None
            user = conn.execute(
                "SELECT * FROM users WHERE id = ?",
                (row["user_id"],),
            ).fetchone()
            if user is None or not _user_row_is_active(user):
                return None

            expires_at = row["expires_at"]
            if ttl_seconds is not None:
                expires_at = _format_timestamp(now + timedelta(seconds=ttl_seconds))
            conn.execute(
                """
                UPDATE sessions
                SET last_seen_at = ?,
                    expires_at = ?
                WHERE id_hash = ?
                """,
                (_format_timestamp(now), expires_at, id_hash),
            )
            updated = conn.execute(
                "SELECT * FROM sessions WHERE id_hash = ?",
                (id_hash,),
            ).fetchone()
        return _session_from_row(updated)

    def delete_session(self, raw_session_id: str) -> None:
        self.ensure_schema()
        id_hash = hash_secret(raw_session_id)
        with self._connect() as conn:
            conn.execute("DELETE FROM sessions WHERE id_hash = ?", (id_hash,))

    def delete_sessions_for_user(self, user_id: str) -> int:
        self.ensure_schema()
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
        return int(cursor.rowcount)

    def create_password_reset_token(
        self,
        user_id: str,
        code_hash: str,
        *,
        ttl_seconds: int = 900,
    ) -> PasswordResetTokenRecord:
        self.ensure_schema()
        token_id = uuid.uuid4().hex
        normalized_code_hash = _require_text(code_hash, "code_hash")
        created_at = _utc_now_dt()
        expires_at = created_at + timedelta(seconds=ttl_seconds)

        with self._connect() as conn:
            self._get_user_by_id(conn, user_id)
            conn.execute(
                """
                INSERT INTO password_reset_tokens (
                    id,
                    user_id,
                    code_hash,
                    created_at,
                    expires_at,
                    used_at,
                    attempt_count
                )
                VALUES (?, ?, ?, ?, ?, NULL, 0)
                """,
                (
                    token_id,
                    user_id,
                    normalized_code_hash,
                    _format_timestamp(created_at),
                    _format_timestamp(expires_at),
                ),
            )
            return self._get_password_reset_token_by_id(conn, token_id)

    def get_password_reset_token(
        self,
        token_id: str,
    ) -> PasswordResetTokenRecord | None:
        self.ensure_schema()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM password_reset_tokens WHERE id = ?",
                (token_id,),
            ).fetchone()
        if row is None or row["used_at"] is not None or _is_expired(row["expires_at"]):
            return None
        return _password_reset_token_from_row(row)

    def increment_password_reset_attempts(
        self,
        token_id: str,
    ) -> PasswordResetTokenRecord:
        self.ensure_schema()
        with self._connect() as conn:
            token = self._get_password_reset_token_by_id(conn, token_id)
            if _is_expired(token.expires_at):
                raise ValueError("password reset token expired")
            if token.used_at is not None:
                raise ValueError("password reset token already used")
            conn.execute(
                """
                UPDATE password_reset_tokens
                SET attempt_count = attempt_count + 1
                WHERE id = ?
                """,
                (token_id,),
            )
            return self._get_password_reset_token_by_id(conn, token_id)

    def mark_password_reset_token_used(
        self,
        token_id: str,
    ) -> PasswordResetTokenRecord:
        self.ensure_schema()
        used_at = _utc_now()
        with self._connect() as conn:
            token = self._get_password_reset_token_by_id(conn, token_id)
            if _is_expired(token.expires_at):
                raise ValueError("password reset token expired")
            if token.used_at is not None:
                raise ValueError("password reset token already used")
            cursor = conn.execute(
                """
                UPDATE password_reset_tokens
                SET used_at = ?
                WHERE id = ?
                  AND used_at IS NULL
                """,
                (used_at, token_id),
            )
            if cursor.rowcount != 1:
                raise ValueError("password reset token already used")
            return self._get_password_reset_token_by_id(conn, token_id)

    def delete_password_reset_token(self, token_id: str) -> int:
        self.ensure_schema()
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM password_reset_tokens WHERE id = ?",
                (token_id,),
            )
        return int(cursor.rowcount)

    def _get_password_reset_token_by_id(
        self,
        conn: sqlite3.Connection,
        token_id: str,
    ) -> PasswordResetTokenRecord:
        row = conn.execute(
            "SELECT * FROM password_reset_tokens WHERE id = ?",
            (token_id,),
        ).fetchone()
        if row is None:
            raise ValueError("password reset token not found")
        return _password_reset_token_from_row(row)


def bootstrap_admin_from_env(store: UserStore) -> BootstrapResult:
    if store.count_users() > 0:
        return BootstrapResult(created=False, reason="users_exist")

    email = os.environ.get("TRADINGAGENTS_ADMIN_EMAIL", "").strip()
    password = os.environ.get("TRADINGAGENTS_ADMIN_PASSWORD", "").strip()
    tenant_id = os.environ.get("TRADINGAGENTS_ADMIN_TENANT_ID", "").strip()
    if not email or not password or not tenant_id:
        return BootstrapResult(created=False, reason="missing_env")

    username = os.environ.get("TRADINGAGENTS_ADMIN_USERNAME", "").strip()
    if not username:
        username = email.split("@", 1)[0]
    display_name = os.environ.get("TRADINGAGENTS_ADMIN_DISPLAY_NAME", "").strip()
    if not display_name:
        display_name = username

    validate_password_policy(password, username=username, email=email)
    password_record = hash_password(password)
    user = store.create_user(
        username=username,
        email=email,
        display_name=display_name,
        role="admin",
        tenant_id=tenant_id,
        password_hash=password_record.encoded_hash,
        password_salt=password_record.salt,
        password_updated_at=_utc_now(),
        must_change_password=True,
    )
    return BootstrapResult(created=True, user_id=user.id)
