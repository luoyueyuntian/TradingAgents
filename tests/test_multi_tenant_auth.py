"""Account login and session-bound tenant selection."""
from fastapi.testclient import TestClient

from web.app import app
from web.passwords import hash_password
from web.user_store import UserStore


def setup_account(monkeypatch, tmp_path):
    monkeypatch.setenv('TRADINGAGENTS_WEB_AUTH_DB', str(tmp_path / 'auth.db'))
    monkeypatch.delenv('TRADINGAGENTS_WEB_API_TOKEN', raising=False)
    store = UserStore(tmp_path / 'auth.db')
    password = hash_password('StrongPass123!')
    members = []
    for tenant, role in [('a', 'admin'), ('b', 'viewer')]:
        store.create_tenant(tenant, display_name=f'Tenant {tenant}')
        members.append(store.create_user(username='alice', email='alice@example.com',
            display_name='Alice', role=role, tenant_id=tenant,
            password_hash=password.encoded_hash, password_salt=password.salt,
            must_change_password=False))
    return TestClient(app), store, members


def login(client):
    return client.post('/api/auth/login', json={'identifier': 'alice@example.com', 'password': 'StrongPass123!'})


def test_login_without_tenant_and_switch_persists_last_visit(monkeypatch, tmp_path):
    client, store, members = setup_account(monkeypatch, tmp_path)
    response = login(client)
    assert response.status_code == 200, response.text
    assert response.json()['user']['tenant_id'] == 'a'
    assert {m['tenant_id'] for m in response.json()['tenants']} == {'a', 'b'}
    response = client.post('/api/auth/switch-tenant', json={'tenant_id': 'b'})
    assert response.status_code == 200, response.text
    assert response.json()['user']['role'] == 'viewer'
    assert response.json()['user']['member_id'] == members[1].id
    assert client.get('/api/admin/users').status_code == 403
    client.post('/api/auth/logout')
    assert login(client).json()['user']['tenant_id'] == 'b'


def test_switch_denies_nonmember_and_preserves_context(monkeypatch, tmp_path):
    client, store, _ = setup_account(monkeypatch, tmp_path)
    assert login(client).status_code == 200
    store.create_tenant('outsider', display_name='Other')
    assert client.post('/api/auth/switch-tenant', json={'tenant_id': 'outsider'}).status_code == 403
    assert client.get('/api/auth/me').json()['user']['tenant_id'] == 'a'


def test_other_device_keeps_active_tenant(monkeypatch, tmp_path):
    client, _, _ = setup_account(monkeypatch, tmp_path)
    second = TestClient(app)
    assert login(client).status_code == 200
    assert login(second).status_code == 200
    assert client.post('/api/auth/switch-tenant', json={'tenant_id': 'b'}).status_code == 200
    assert second.get('/api/auth/me').json()['user']['tenant_id'] == 'a'


def test_unavailable_current_tenant_allows_recovery(monkeypatch, tmp_path):
    client, store, _ = setup_account(monkeypatch, tmp_path)
    assert login(client).status_code == 200
    # Direct fixture mutation bypasses last global admin guard, emulating expiration.
    with store._connect() as conn:
        conn.execute("UPDATE tenants SET disabled=1 WHERE tenant_id='a'")
    assert client.get('/api/auth/tenants').status_code == 200
    assert client.get('/api/auth/me').status_code == 200
    assert client.post('/api/auth/switch-tenant', json={'tenant_id': 'b'}).status_code == 200


def test_account_with_no_accessible_memberships_can_login(monkeypatch, tmp_path):
    client, store, _ = setup_account(monkeypatch, tmp_path)
    with store._connect() as conn:
        conn.execute('UPDATE tenants SET disabled=1')
    response = login(client)
    assert response.status_code == 200, response.text
    assert response.json()['tenants'] == []
    assert not response.json()['user']['tenant_id']
    assert client.get('/api/runs').status_code == 403
    assert client.post('/api/auth/logout').status_code == 200


def test_tenant_admin_cannot_change_shared_identity_or_password(monkeypatch, tmp_path):
    client, store, members = setup_account(monkeypatch, tmp_path)
    assert login(client).status_code == 200
    target = members[1]
    # Switch member is a viewer, only current tenant admin may manage local members.
    response = client.patch(f'/api/admin/users/{members[0].id}', json={'email': 'hijack@example.com'})
    assert response.status_code == 403
    response = client.post(f'/api/admin/users/{members[0].id}/reset-password')
    assert response.status_code == 403
    assert store.get_user(target.id).email == 'alice@example.com'


def test_adding_existing_account_never_returns_new_password(monkeypatch, tmp_path):
    client, store, _ = setup_account(monkeypatch, tmp_path)
    other_password = hash_password('OtherPass456!')
    bob = store.create_user(username='bob', email='bob@example.com', display_name='Bob', role='viewer',
        tenant_id='b', password_hash=other_password.encoded_hash, password_salt=other_password.salt,
        must_change_password=False)
    assert login(client).status_code == 200
    response = client.post('/api/admin/users/memberships', json={'email': 'bob@example.com', 'role': 'analyst'})
    assert response.status_code == 201, response.text
    assert response.json()['temporary_password'] == ''
    assert store.get_user(bob.id).password_hash == other_password.encoded_hash


def test_profile_change_is_shared_and_available_without_tenants(monkeypatch, tmp_path):
    client, store, members = setup_account(monkeypatch, tmp_path)
    assert login(client).status_code == 200
    assert client.post('/api/auth/switch-tenant', json={'tenant_id': 'b'}).status_code == 200
    assert client.put('/api/auth/profile', json={'display_name': 'Shared Alice'}).status_code == 200
    assert store.get_user(members[0].id).display_name == 'Shared Alice'
    with store._connect() as conn:
        conn.execute('UPDATE tenants SET disabled=1')
    assert client.get('/api/auth/profile').status_code == 200
    assert client.post('/api/auth/change-password', json={'new_password': 'UpdatedPass456!'}).status_code == 200
    assert client.get('/api/auth/me').status_code == 200


def test_password_recovery_revokes_all_account_sessions(monkeypatch, tmp_path):
    from web.passwords import hash_verification_code
    client, store, members = setup_account(monkeypatch, tmp_path)
    assert login(client).status_code == 200
    raw, _ = store.create_session(members[1].id)
    token = store.create_password_reset_token(members[0].id, hash_verification_code('123456'))
    response = client.post('/api/auth/password-reset/confirm', json={
        'reset_id': token.id, 'code': '123456', 'new_password': 'RecoveredPass456!'})
    assert response.status_code == 200
    assert store.get_session(raw) is None
    assert client.get('/api/auth/me').status_code == 401


def test_stale_tab_write_rejected_before_business_handler(monkeypatch, tmp_path):
    import web.admin_user_routes as routes
    client, store, members = setup_account(monkeypatch, tmp_path)
    assert login(client).status_code == 200
    # Both tenants allow administration: rejection must come from stale context.
    with store._connect() as conn:
        conn.execute("UPDATE users SET role='admin' WHERE id=?", (members[1].id,))
    assert client.post('/api/auth/switch-tenant', json={'tenant_id': 'b'}).status_code == 200
    called = []
    monkeypatch.setattr(routes, 'create_managed_user_for_tenant', lambda *args: called.append(args))
    response = client.post('/api/admin/users', headers={'X-TradingAgents-Session-Tenant': 'a'},
        json={'username': 'newuser', 'email': 'new@example.com', 'display_name': 'New', 'role': 'viewer', 'password': 'StrongPass123!'})
    assert response.status_code == 409
    assert response.json()['code'] == 'tenant_context_mismatch'
    assert called == []
    assert store.get_account_by_identifier('new@example.com') is None
    # Auth identity remains available to recover the tab regardless of its old marker.
    assert client.get('/api/auth/me', headers={'X-TradingAgents-Session-Tenant': 'a'}).json()['user']['tenant_id'] == 'b'


def test_authenticated_request_uses_read_only_schema_fast_path(monkeypatch, tmp_path):
    client, store, _ = setup_account(monkeypatch, tmp_path)
    assert login(client).status_code == 200
    statements = []
    connect = UserStore._connect
    from contextlib import contextmanager
    @contextmanager
    def traced_connect(self):
        with connect(self) as conn:
            conn.set_trace_callback(statements.append)
            yield conn
    monkeypatch.setattr(UserStore, '_connect', traced_connect)
    assert client.get('/api/auth/me').status_code == 200
    normalized = [s.upper() for s in statements]
    assert not any('BEGIN IMMEDIATE' in s or 'ALTER TABLE' in s for s in normalized)
    assert not any(s.strip() == 'SELECT * FROM USERS' for s in normalized)
    assert any('U.ACCOUNT_ID=' in s for s in normalized)
