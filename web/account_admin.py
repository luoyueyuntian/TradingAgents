"""Local operator commands for account migration review and credential recovery.

Run with the same filesystem privileges as the service, never through an HTTP route.
"""
from __future__ import annotations

import argparse
import json
import secrets
import sqlite3
from pathlib import Path

from tradingagents.service.timestamps import current_timestamp_ms
from tradingagents.service.web_state import get_web_auth_db_path
from web.passwords import hash_password
from web.user_store import UserStore


def preview_migration(db_path: Path) -> dict:
    """Preview pending legacy rows only, without migrating or touching credentials.

    Counts describe pending accounts and members; a fully migrated database returns zero.
    """
    with sqlite3.connect(db_path.resolve().as_uri() + '?mode=ro', uri=True) as conn:
        conn.row_factory = sqlite3.Row
        columns = {r['name'] for r in conn.execute('PRAGMA table_info(users)')}
        rows = conn.execute('SELECT id, username, email, tenant_id FROM users' + (' WHERE account_id IS NULL' if 'account_id' in columns else '') + ' ORDER BY created_at, id').fetchall()
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        existing = conn.execute('SELECT username,email,requires_password_reset FROM accounts').fetchall() if 'accounts' in tables else []
    from web.account_migration import plan_accounts
    accounts = plan_accounts(rows, existing)
    return {'accounts': accounts, 'account_count': len(accounts), 'member_count': len(rows)}


def recover_account(store: UserStore, identifier: str) -> str:
    """Issue a temporary password atomically; caller delivers it privately."""
    account = store.get_account_by_identifier(identifier)
    if account is None:
        raise ValueError('Account not found')
    temporary = secrets.token_urlsafe(24) + 'A1!'
    password = hash_password(temporary)
    with store._connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        store._update_account_in_connection(conn, account.account_id, {
            'password_hash': password.encoded_hash,
            'password_salt': password.salt,
            'password_updated_at': current_timestamp_ms(),
            'must_change_password': True,
        })
        conn.execute('DELETE FROM sessions WHERE user_id=?', (account.account_id,))
        conn.execute('DELETE FROM password_reset_tokens WHERE user_id=?', (account.account_id,))
    store.record_audit_event('operator.account_recovered', target_user_id=account.account_id)
    return temporary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db', type=Path, default=get_web_auth_db_path())
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('preview-migration', help='Read-only mapping and conflict report')
    recovery = commands.add_parser('recover', help='Issue a temporary account password')
    recovery.add_argument('--email', required=True)
    args = parser.parse_args()
    if args.command == 'preview-migration':
        print(json.dumps(preview_migration(args.db), ensure_ascii=False, indent=2))
    else:
        print(recover_account(UserStore(args.db), args.email))


if __name__ == '__main__':
    main()
