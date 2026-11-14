import pytest

from tests.test_auth_routes import _auth_client, _create_user, _login


def setup(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    user = _create_user(store, role='viewer', must_change_password=False)
    _login(client)
    return client, store, user


def test_profile_requires_session(monkeypatch, tmp_path):
    client, store = _auth_client(monkeypatch, tmp_path)
    _create_user(store, must_change_password=False)
    assert client.get('/api/auth/profile').status_code == 401


def test_viewer_can_update_own_nickname_but_not_privileges(monkeypatch, tmp_path):
    client, store, user = setup(monkeypatch, tmp_path)
    response = client.put('/api/auth/profile', json={'display_name': 'New Name', 'role': 'admin', 'email': 'other@example.com'})
    assert response.status_code == 422
    response = client.put('/api/auth/profile', json={'display_name': 'New Name'})
    assert response.status_code == 200
    assert store.get_user(user.id).display_name == 'New Name'
    assert store.get_user(user.id).role == 'viewer'
    assert client.get('/api/auth/profile').json()['user']['username'] == 'alice'


def test_revoke_others_keeps_current_and_other_users(monkeypatch, tmp_path):
    client, store, user = setup(monkeypatch, tmp_path)
    other, _ = store.create_session(user.id)
    stranger = _create_user(store, username='bob', email='bob@example.com', must_change_password=False)
    unrelated, _ = store.create_session(stranger.id)
    assert len(client.get('/api/auth/profile').json()['sessions']) == 2
    assert client.post('/api/auth/profile/sessions/revoke-others').status_code == 200
    assert store.get_session(other) is None
    assert store.get_session(unrelated) is not None
    assert client.get('/api/auth/me').status_code == 200


def test_email_verification_is_required_and_single_use(monkeypatch, tmp_path):
    from web import profile_routes
    client, store, user = setup(monkeypatch, tmp_path)
    sent = []
    monkeypatch.setattr(profile_routes, 'get_smtp_settings', lambda: object())
    monkeypatch.setattr(profile_routes, 'send_email_change_code', lambda email, code: sent.append((email, code)))
    assert client.post('/api/auth/profile/email/request', json={'email': 'new@example.com'}).status_code == 200
    assert store.get_user(user.id).email == 'alice@example.com'
    assert client.post('/api/auth/profile/email/request', json={'email': 'new@example.com'}).status_code == 429
    assert client.post('/api/auth/profile/email/confirm', json={'code': 'wrong'}).status_code in {400, 422}
    assert client.post('/api/auth/profile/email/confirm', json={'code': sent[0][1]}).status_code == 200
    assert store.get_user(user.id).email == 'new@example.com'
    assert client.post('/api/auth/profile/email/confirm', json={'code': sent[0][1]}).status_code == 400


def test_smtp_unavailable_does_not_claim_email_was_sent(monkeypatch, tmp_path):
    from web import profile_routes
    client, store, user = setup(monkeypatch, tmp_path)
    monkeypatch.setattr(profile_routes, 'get_smtp_settings', lambda: None)
    assert client.post('/api/auth/profile/email/request', json={'email':'new@example.com'}).status_code == 503
    assert store.get_user(user.id).email == 'alice@example.com'


@pytest.mark.parametrize('failure', ['expired', 'locked', 'delivery'])
def test_email_failures_keep_original_address(monkeypatch, tmp_path, failure):
    from web import profile_routes
    client, store, user = setup(monkeypatch, tmp_path)
    sent = []
    monkeypatch.setattr(profile_routes, 'get_smtp_settings', lambda: object())
    def send(email, code):
        if failure == 'delivery':
            raise RuntimeError('smtp secret must not leak')
        sent.append(code)
    monkeypatch.setattr(profile_routes, 'send_email_change_code', send)
    response = client.post('/api/auth/profile/email/request', json={'email': 'new@example.com'})
    if failure == 'delivery':
        assert response.status_code == 502
        assert 'secret' not in response.text
    else:
        assert response.status_code == 200
        if failure == 'expired':
            with profile_routes.profile_db(store) as conn:
                conn.execute('UPDATE email_changes SET expires_at=0 WHERE user_id=?', (user.id,))
        else:
            for _ in range(5):
                wrong = '000000' if sent[0] != '000000' else '111111'
                assert client.post('/api/auth/profile/email/confirm', json={'code': wrong}).status_code == 400
        assert client.post('/api/auth/profile/email/confirm', json={'code': sent[0]}).status_code == 400
    assert store.get_user(user.id).email == 'alice@example.com'
