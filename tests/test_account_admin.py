"""Operator-only fallback for accounts requiring recovery without SMTP."""
from web.passwords import hash_password, verify_password
from web.user_store import UserStore


def test_operator_recovery_revokes_credentials_and_requires_change(tmp_path):
    from web.account_admin import recover_account
    store = UserStore(tmp_path / 'auth.db')
    store.create_tenant('a', display_name='A')
    password = hash_password('OriginalPass123!')
    member = store.create_user(username='alice', email='alice@example.com', display_name='Alice',
        role='viewer', tenant_id='a', password_hash=password.encoded_hash, password_salt=password.salt,
        must_change_password=False)
    raw, _ = store.create_session(member.id)
    token = store.create_password_reset_token(member.id, 'unused')
    temporary_password = recover_account(store, 'alice@example.com')
    user = store.get_account_by_identifier('alice@example.com')
    assert verify_password(temporary_password, user.password_hash, user.password_salt)
    assert not verify_password('OriginalPass123!', user.password_hash, user.password_salt)
    assert user.must_change_password
    assert not user.requires_password_reset
    assert store.get_session(raw) is None
    assert store.get_password_reset_token(token.id) is None


def test_migration_preview_is_read_only_and_matches_reserved_suffixes(tmp_path):
    import sqlite3
    from web.account_admin import preview_migration
    path = tmp_path / 'legacy.db'
    with sqlite3.connect(path) as conn:
        conn.execute('CREATE TABLE users (id TEXT, username TEXT, email TEXT, tenant_id TEXT, created_at INTEGER)')
        conn.executemany('INSERT INTO users VALUES (?,?,?,?,?)', [
            ('1', 'x', 'one@example.com', 'a', 1),
            ('2', 'x', 'two@example.com', 'b', 2),
            ('3', 'x-2', 'three@example.com', 'b', 3),
        ])
    before = path.read_bytes()
    report = preview_migration(path)
    assert [account['username'] for account in report['accounts']] == ['x', 'x-3', 'x-2']
    assert path.read_bytes() == before
    assert all('password' not in key for account in report['accounts'] for key in account)


def test_preview_and_migration_use_fixed_source_names(tmp_path):
    from web.account_admin import preview_migration
    store = UserStore(tmp_path / 'auth.db')
    ids = []
    for index, tenant in enumerate(('a', 'b', 'c')):
        store.create_tenant(tenant, display_name=tenant)
        ids.append(store.create_user(username=f'u{index}', email=f'e{index}@example.com',
            display_name='User', role='viewer', tenant_id=tenant,
            password_hash='hash', password_salt='salt').id)
    with store._connect() as conn:
        conn.execute('PRAGMA user_version=0')
        conn.execute('DELETE FROM accounts')
        conn.execute('UPDATE users SET account_id=NULL')
        for index, (username, email) in enumerate((('sam', 'same@example.com'), ('sam-2', 'same@example.com'), ('sam', 'other@example.com'))):
            conn.execute('UPDATE users SET username=?,email=?,created_at=? WHERE id=?', (username, email, index+1, ids[index]))
    preview = preview_migration(store.db_path)
    store.ensure_schema()
    assert [a['username'] for a in preview['accounts']] == ['sam', 'sam-3']
    assert all(store.get_account_by_identifier(a['email']).username == a['username'] for a in preview['accounts'])


def test_pending_preview_reserves_existing_account_names(tmp_path):
    from web.account_admin import preview_migration
    store = UserStore(tmp_path / 'auth.db')
    for tenant in ('a', 'b'):
        store.create_tenant(tenant, display_name=tenant)
    store.create_user(username='sam', email='existing@example.com', display_name='Existing',
        role='viewer', tenant_id='a', password_hash='hash', password_salt='salt')
    pending = store.create_user(username='legacy', email='pending@example.com', display_name='Pending',
        role='viewer', tenant_id='b', password_hash='hash', password_salt='salt')
    with store._connect() as conn:
        conn.execute('PRAGMA user_version=0')
        conn.execute('DELETE FROM accounts WHERE id=?', (pending.account_id,))
        conn.execute('UPDATE users SET account_id=NULL,username=? WHERE id=?', ('sam', pending.id))
    report = preview_migration(store.db_path)
    assert report['account_count'] == 1
    assert report['accounts'][0]['username'] == 'sam-2'
    store.ensure_schema()
    assert store.get_account_by_identifier('pending@example.com').username == 'sam-2'
    assert preview_migration(store.db_path)['account_count'] == 0


def test_preview_never_reads_existing_account_credentials(monkeypatch, tmp_path):
    import sqlite3
    from web.account_admin import preview_migration
    store = UserStore(tmp_path / 'auth.db')
    store.create_tenant('a', display_name='A')
    store.create_user(username='existing', email='existing@example.com', display_name='Existing',
        role='viewer', tenant_id='a', password_hash='hash', password_salt='salt')
    before = store.db_path.read_bytes()
    connect = sqlite3.connect
    denied_reads = []
    def guarded_connect(*args, **kwargs):
        conn = connect(*args, **kwargs)
        def authorize(action, table, column, database, source):
            if action == sqlite3.SQLITE_READ and table == 'accounts' and column in {'password_hash', 'password_salt'}:
                denied_reads.append(column)
                return sqlite3.SQLITE_DENY
            return sqlite3.SQLITE_OK
        conn.set_authorizer(authorize)
        return conn
    monkeypatch.setattr(sqlite3, 'connect', guarded_connect)
    assert preview_migration(store.db_path)['account_count'] == 0
    assert denied_reads == []
    assert store.db_path.read_bytes() == before
