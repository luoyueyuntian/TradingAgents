import pytest

from tests.test_auth_routes import _auth_client, _create_user
from web.passwords import verify_password


def guest_setup(monkeypatch,tmp_path):
    from web.guest_access import register_public_guest
    client,store=_auth_client(monkeypatch,tmp_path)
    user=_create_user(store,username='guest',email='guest@demo.invalid',role='viewer',must_change_password=False)
    register_public_guest(store,user.account_id,'tenant-a','guest','StrongPass123!')
    login=client.post('/api/auth/login',json={'identifier':'guest','password':'StrongPass123!'})
    assert login.status_code==200
    assert login.json()['user']['is_guest'] is True
    return client,store,user


def test_guest_credentials_are_visible_without_login_and_guest_can_browse(monkeypatch,tmp_path):
    client,store,user=guest_setup(monkeypatch,tmp_path)
    client.cookies.clear()
    data=client.get('/api/auth/guest')
    assert data.status_code==200
    assert data.json()['username']=='guest' and data.json()['password']=='StrongPass123!'
    assert 'account_id' not in data.json()
    client.post('/api/auth/login',json={'identifier':'guest','password':'StrongPass123!'})
    assert client.get('/api/providers').status_code==200
    assert client.get('/api/auth/profile').status_code==200


@pytest.mark.parametrize('method,path,body',[
 ('PUT','/api/settings',{'llm':{'provider':'openai'}}),
 ('POST','/api/runs',{}),('POST','/api/notifications/read-all',{}),
 ('PUT','/api/auth/profile',{'display_name':'Changed'}),
 ('POST','/api/auth/profile/email/request',{'email':'someone@example.com'}),
 ('POST','/api/auth/profile/sessions/revoke-others',{}),
 ('POST','/api/auth/change-password',{'old_password':'StrongPass123!','new_password':'ChangedPass123!'}),
 ('POST','/api/auth/switch-tenant',{'tenant_id':'other'}),
])
def test_public_guest_cannot_mutate_system_business_or_shared_account(monkeypatch,tmp_path,method,path,body):
    client,store,user=guest_setup(monkeypatch,tmp_path)
    assert client.request(method,path,json=body).status_code==403
    fresh=store.get_account_user(user.account_id)
    assert verify_password('StrongPass123!',fresh.password_hash,fresh.password_salt)


def test_regular_viewer_can_still_change_own_profile(monkeypatch,tmp_path):
    client,store=_auth_client(monkeypatch,tmp_path)
    _create_user(store,role='viewer',must_change_password=False)
    client.post('/api/auth/login',json={'identifier':'alice','password':'StrongPass123!'})
    assert client.put('/api/auth/profile',json={'display_name':'Updated'}).status_code==200


def test_guest_panel_disappears_if_role_is_elevated_and_session_fails_closed(monkeypatch,tmp_path):
    client,store,user=guest_setup(monkeypatch,tmp_path)
    store.update_user(user.id,role='admin')
    assert client.get('/api/auth/guest').json() is None
    assert client.get('/api/settings').status_code==403
    assert client.get('/api/providers').status_code==403


def test_guest_stock_lookup_does_not_refresh_the_shared_catalog(monkeypatch,tmp_path):
    from tradingagents.service.stock_catalog import StockCatalogItem
    from web import routes
    client,store,user=guest_setup(monkeypatch,tmp_path)
    calls=[]
    monkeypatch.setattr(routes,'stock_catalog_needs_refresh',lambda:True)
    monkeypatch.setattr(routes,'search_stock_catalog',lambda *args,**kwargs:[StockCatalogItem('hk','0700.HK','腾讯控股','HKEX')])
    monkeypatch.setattr(routes,'refresh_stock_catalog',lambda **kwargs:calls.append('refresh'))
    assert client.get('/api/stocks?market=hk').status_code==200
    assert calls==[]
