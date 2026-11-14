"""Account identities and tenant membership projections."""

from dataclasses import replace
import secrets

SHARED = (
    "username",
    "email",
    "display_name",
    "password_hash",
    "password_salt",
    "password_updated_at",
    "must_change_password",
    "last_login_at",
)


class AccountStoreMixin:
    def _ensure_accounts(self, conn):
        from web.user_store import _utc_now

        conn.execute(
            "CREATE TABLE IF NOT EXISTS accounts (id TEXT PRIMARY KEY, username TEXT NOT NULL, email TEXT NOT NULL, display_name TEXT NOT NULL, password_hash TEXT NOT NULL, password_salt TEXT NOT NULL, password_updated_at INTEGER, must_change_password INTEGER NOT NULL, last_login_at INTEGER, disabled INTEGER DEFAULT 0, deleted_at INTEGER, expires_at INTEGER, created_at INTEGER, updated_at INTEGER, last_tenant_id TEXT, requires_password_reset INTEGER DEFAULT 0)"
        )
        migrating_sessions = "active_tenant_id" not in {
            r["name"] for r in conn.execute("PRAGMA table_info(sessions)")
        }
        for table, column, kind in [
            ("users", "account_id", "TEXT"),
            ("sessions", "active_tenant_id", "TEXT"),
        ]:
            if column not in {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {kind}")
        if migrating_sessions:
            conn.execute("DELETE FROM sessions")
        from web.account_migration import plan_accounts
        source_rows = conn.execute("SELECT * FROM users ORDER BY created_at,id").fetchall()
        existing_accounts = conn.execute("SELECT * FROM accounts").fetchall()
        planned = plan_accounts([r for r in source_rows if not r["account_id"]], existing_accounts)
        groups = {}
        for row in source_rows:
            if not row["account_id"]:
                groups.setdefault(row["email"].strip().casefold(), []).append(row)
        usernames = {p["email"]: p["username"] for p in planned}
        for email, rows in groups.items():
            existing = next(
                (
                    r
                    for r in conn.execute("SELECT * FROM accounts")
                    if r["email"].casefold() == email
                ),
                None,
            )
            aid = existing["id"] if existing else rows[0]["id"]
            if not existing:
                row = rows[0]
                values = dict(row)
                username = usernames[email]
                values.update(id=aid, username=username, email=row["email"].strip())
                cols = ["id", *SHARED, "created_at", "updated_at"]
                conn.execute(
                    f"INSERT INTO accounts ({','.join(cols)}) VALUES ({','.join('?' for _ in cols)})",
                    [values[c] for c in cols],
                )
            merged = len(rows) > 1
            for row in rows:
                conn.execute("UPDATE users SET account_id=? WHERE id=?", (aid, row["id"]))
                conn.execute(
                    "UPDATE sessions SET user_id=?,active_tenant_id=? WHERE user_id=?",
                    (aid, row["tenant_id"], row["id"]),
                )
                conn.execute(
                    "UPDATE password_reset_tokens SET user_id=? WHERE user_id=?", (aid, row["id"])
                )
            if merged:
                conn.execute(
                    "UPDATE accounts SET password_hash=?,requires_password_reset=1,must_change_password=1 WHERE id=?",
                    (secrets.token_hex(64), aid),
                )
                conn.execute("DELETE FROM sessions WHERE user_id=?", (aid,))
                conn.execute("DELETE FROM password_reset_tokens WHERE user_id=?", (aid,))
            account = conn.execute("SELECT * FROM accounts WHERE id=?", (aid,)).fetchone()
            conn.execute(
                "UPDATE users SET " + ",".join(f"{c}=?" for c in SHARED) + " WHERE account_id=?",
                [account[c] for c in SHARED] + [aid],
            )

    def _resolve_account_id(self, conn, identity):
        row = conn.execute("SELECT account_id FROM users WHERE id=?", (identity,)).fetchone()
        return row["account_id"] if row else identity

    def get_account_user(self, account_id):
        from web.user_store import _user_from_row

        self.ensure_schema()
        with self._connect() as conn:
            row = conn.execute(
                "SELECT *,id AS account_id,'' AS tenant_id,'viewer' AS role FROM accounts WHERE id=?",
                (account_id,),
            ).fetchone()
        return (
            replace(
                _user_from_row(row), requires_password_reset=bool(row["requires_password_reset"])
            )
            if row
            else None
        )

    def get_account_by_identifier(self, identifier):
        self.ensure_schema()
        normalized = identifier.strip().casefold()
        with self._connect() as conn:
            matches = [
                r["id"]
                for r in conn.execute("SELECT id,email,username FROM accounts")
                if normalized in (r["email"].casefold(), r["username"].casefold())
            ]
        return self.get_account_user(matches[0]) if len(matches) == 1 else None

    def list_account_memberships(self, account_id):
        from web.user_store import user_is_expired, tenant_is_expired

        from web.user_store import _user_from_row
        self.ensure_schema()
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT u.*, t.expires_at AS tenant_expires_at FROM users u "
                "JOIN tenants t ON t.tenant_id=u.tenant_id "
                "WHERE u.account_id=? AND u.deleted_at IS NULL AND u.disabled=0 "
                "AND t.disabled=0 AND t.archived=0", (account_id,),
            ).fetchall()
        from web.user_store import tenant_is_expired_value
        return [_user_from_row(row) for row in rows
                if not user_is_expired(_user_from_row(row))
                and not tenant_is_expired_value(row["tenant_expires_at"])]

    def select_account_tenant(self, account_id):
        members = sorted(
            self.list_account_memberships(account_id), key=lambda m: (m.created_at, m.tenant_id)
        )
        with self._connect() as conn:
            row = conn.execute(
                "SELECT last_tenant_id FROM accounts WHERE id=?", (account_id,)
            ).fetchone()
        return next(
            (m for m in members if row and m.tenant_id == row["last_tenant_id"]),
            members[0] if members else self.get_account_user(account_id),
        )

    def create_session(self, user_id, *, ttl_seconds=43200):
        from web.user_store import _utc_now, _session_from_row, secrets
        from web.passwords import hash_secret

        self.ensure_schema()
        raw = secrets.token_urlsafe(32)
        now = _utc_now()
        with self._connect() as conn:
            from web.user_store import _user_row_is_active, tenant_is_expired_value

            conn.execute("BEGIN IMMEDIATE")
            aid = self._resolve_account_id(conn, user_id)
            account = conn.execute("SELECT * FROM accounts WHERE id=?", (aid,)).fetchone()
            if account is None or not _user_row_is_active(account):
                raise ValueError("account not active")
            members = [
                member
                for member in conn.execute(
                    "SELECT u.*, t.expires_at AS tenant_expires_at FROM users u "
                    "JOIN tenants t ON t.tenant_id=u.tenant_id "
                    "WHERE u.account_id=? AND t.disabled=0 AND t.archived=0 "
                    "ORDER BY u.created_at, u.tenant_id",
                    (aid,),
                )
                if _user_row_is_active(member)
                and not tenant_is_expired_value(member["tenant_expires_at"])
            ]
            selected = next(
                (member for member in members if member["tenant_id"] == account["last_tenant_id"]),
                members[0] if members else None,
            )
            selected_tenant = selected["tenant_id"] if selected is not None else None
            if selected_tenant:
                conn.execute(
                    "UPDATE accounts SET last_tenant_id=? WHERE id=?", (selected_tenant, aid)
                )
            conn.execute(
                "INSERT INTO sessions VALUES (?,?,?,?,?,?)",
                (
                    hash_secret(raw),
                    aid,
                    now,
                    now,
                    now + ttl_seconds * 1000,
                    selected_tenant,
                ),
            )
            row = conn.execute(
                "SELECT * FROM sessions WHERE id_hash=?", (hash_secret(raw),)
            ).fetchone()
        return raw, _session_from_row(row)

    def get_session_user(self, raw_session_id):
        session = self.get_session(raw_session_id)
        if not session:
            return None
        from web.user_store import _user_from_row, _user_row_is_active, tenant_is_expired_value
        with self._connect() as conn:
            row = conn.execute(
                "SELECT u.*,t.expires_at AS tenant_expires_at FROM users u "
                "JOIN tenants t ON t.tenant_id=u.tenant_id "
                "WHERE u.account_id=? AND u.tenant_id=? AND t.disabled=0 AND t.archived=0",
                (session.user_id, session.active_tenant_id),
            ).fetchone()
        if row is not None and _user_row_is_active(row) and not tenant_is_expired_value(row["tenant_expires_at"]):
            return _user_from_row(row)
        return self.get_account_user(session.user_id)

    def switch_session_tenant(self, raw_session_id, tenant_id):
        from web.passwords import hash_secret

        session = self.get_session(raw_session_id)
        if not session:
            raise ValueError("session not found")
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            from web.user_store import (
                _user_from_row,
                _user_row_is_active,
                tenant_is_expired_value,
                _is_expired,
            )

            current = conn.execute(
                "SELECT * FROM sessions WHERE id_hash=?", (hash_secret(raw_session_id),)
            ).fetchone()
            if current is None or _is_expired(current["expires_at"]):
                raise ValueError("session not found")
            row = conn.execute(
                "SELECT u.* FROM users u JOIN tenants t ON t.tenant_id=u.tenant_id WHERE u.account_id=? AND u.tenant_id=? AND t.disabled=0 AND t.archived=0",
                (session.user_id, tenant_id),
            ).fetchone()
            tenant = conn.execute(
                "SELECT expires_at FROM tenants WHERE tenant_id=?", (tenant_id,)
            ).fetchone()
            if (
                row is None
                or not _user_row_is_active(row)
                or tenant_is_expired_value(tenant["expires_at"])
            ):
                raise ValueError("tenant access denied")
            member = _user_from_row(row)
            conn.execute(
                "UPDATE sessions SET active_tenant_id=? WHERE id_hash=?",
                (tenant_id, hash_secret(raw_session_id)),
            )
            conn.execute(
                "UPDATE accounts SET last_tenant_id=? WHERE id=?", (tenant_id, session.user_id)
            )
        return member

    def _update_account_in_connection(self, conn, account_id, fields):
        from web.user_store import _utc_now

        allowed = set(SHARED) | {"requires_password_reset"}
        if set(fields) - allowed:
            raise ValueError("unsupported account field")
        current = conn.execute("SELECT * FROM accounts WHERE id=?", (account_id,)).fetchone()
        if current is None:
            raise ValueError("account not found")
        fields = dict(fields)
        for key in ("username", "email"):
            if key in fields:
                fields[key] = fields[key].strip()
                if not fields[key]:
                    raise ValueError(f"{key} must not be blank")
                if any(
                    fields[key].casefold() in (r["username"].casefold(), r["email"].casefold())
                    for r in conn.execute("SELECT * FROM accounts WHERE id != ?", (account_id,))
                ):
                    raise ValueError(f"{key} already exists")
        if "password_hash" in fields:
            fields["requires_password_reset"] = 0
        fields["updated_at"] = _utc_now()
        conn.execute(
            "UPDATE accounts SET " + ",".join(f"{k}=?" for k in fields) + " WHERE id=?",
            list(fields.values()) + [account_id],
        )
        shared = {k: v for k, v in fields.items() if k in SHARED or k == "updated_at"}
        if shared:
            conn.execute(
                "UPDATE users SET " + ",".join(f"{k}=?" for k in shared) + " WHERE account_id=?",
                list(shared.values()) + [account_id],
            )

    def update_account(self, account_id, **fields):
        self.ensure_schema()
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            self._update_account_in_connection(conn, account_id, fields)
        return self.get_account_user(account_id)
