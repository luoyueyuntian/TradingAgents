"""Explicitly public demo credentials; normal account secrets are never exposed.

Registration is an administrator deployment action. This separate registry also
keeps the shared identity read-only if its public login panel is disabled.
"""
from __future__ import annotations

import sqlite3
import time

from tradingagents.service.web_state import get_web_auth_db_path


def guest_record(account_id: str | None = None):
    path = get_web_auth_db_path()
    if not path.exists():
        return None
    with sqlite3.connect(path, timeout=5) as conn:
        conn.row_factory = sqlite3.Row
        try:
            if account_id is None:
                return conn.execute('SELECT * FROM public_guest_accounts WHERE enabled=1 LIMIT 1').fetchone()
            return conn.execute('SELECT * FROM public_guest_accounts WHERE account_id=?', (account_id,)).fetchone()
        except sqlite3.OperationalError as exc:
            if 'no such table: public_guest_accounts' in str(exc):
                return None
            raise


def is_guest_user(user) -> bool:
    return user is not None and guest_record(user.account_id or user.id) is not None


def guest_request_allowed(user, path: str, method: str) -> bool:
    record = guest_record(user.account_id or user.id)
    if record is None:
        return True
    if user.role != 'viewer' or user.tenant_id != record['tenant_id']:
        return False
    if method.upper() == 'POST' and path == '/api/auth/logout':
        return True
    if method.upper() not in {'GET', 'HEAD', 'OPTIONS'}:
        return False
    return not (path.startswith(('/api/settings','/api/admin/','/api/system/')) or path.endswith('/debug-config'))


def register_public_guest(store, account_id: str, tenant_id: str, username: str, password: str):
    from .passwords import verify_password
    account = store.get_account_user(account_id)
    memberships = store.list_account_memberships(account_id)
    if (not account or account.username != username or account.must_change_password
        or account.requires_password_reset or len(memberships) != 1
        or memberships[0].tenant_id != tenant_id or memberships[0].role != 'viewer'
        or not verify_password(password, account.password_hash, account.password_salt)):
        raise ValueError('Public guest must be a valid, single-tenant read-only account with a matching password')
    with sqlite3.connect(store.db_path) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS public_guest_accounts (
            account_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL,
            username TEXT NOT NULL, public_password TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 1
        )''')
        conn.execute('UPDATE public_guest_accounts SET enabled=0')
        conn.execute('INSERT OR REPLACE INTO public_guest_accounts VALUES (?,?,?,?,1)', (account_id,tenant_id,username,password))
        conn.execute('DELETE FROM password_reset_tokens WHERE user_id=?', (account_id,))


def public_guest_credentials():
    from .passwords import verify_password
    from .user_store import UserStore
    record = guest_record()
    if record is None:
        return None
    store = UserStore(get_web_auth_db_path())
    account = store.get_account_user(record['account_id'])
    if (not account or account.disabled or account.deleted_at is not None or account.must_change_password
        or account.requires_password_reset or (account.expires_at is not None and account.expires_at <= int(time.time()*1000))
        or account.username != record['username']
        or not verify_password(record['public_password'],account.password_hash,account.password_salt)):
        return None
    memberships = store.list_account_memberships(account.account_id)
    if len(memberships) != 1 or memberships[0].role != 'viewer' or memberships[0].tenant_id != record['tenant_id']:
        return None
    return {'username':record['username'],'password':record['public_password'],'tenant_id':record['tenant_id']}
