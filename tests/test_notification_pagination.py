from fastapi.testclient import TestClient

from tests.test_web_routes import _make_run
from web import routes
from web.app import app


def test_notification_pagination_and_mark_all_cover_more_than_99(monkeypatch, tmp_path):
    state = {'notifications': {'read_items': []}}
    monkeypatch.setattr(routes, 'get_web_settings_path', lambda tenant_id=None: tmp_path/'settings.json')
    monkeypatch.setattr(routes, 'load_settings', lambda path=None: state)
    monkeypatch.setattr(routes, 'save_settings', lambda settings, path=None: state.update(settings))
    runs=[]
    for i in range(105):
        run=_make_run(f'run-{i}')
        run.status='completed'
        run.created_at=1794700000000+i
        run.signal='Hold'
        runs.append(run)
    monkeypatch.setattr(routes, 'list_runs', lambda tenant_id=None: runs)
    client=TestClient(app)
    first=client.get('/api/notifications?offset=0&limit=20').json()
    second=client.get('/api/notifications?offset=20&limit=20').json()
    assert first['unread_count']==105
    assert first['filtered_count']==105
    assert len(first['items'])==len(second['items'])==20
    assert not {i['id'] for i in first['items']} & {i['id'] for i in second['items']}
    assert len(client.get('/api/notifications').json()['items'])==30
    assert len(client.get('/api/notifications?offset=100&limit=20').json()['items'])==5
    older_id=second['items'][-1]['id']
    assert client.post('/api/notifications/'+older_id+'/read').status_code==200
    result=client.post('/api/notifications/read-all?kind=run')
    assert result.status_code==200
    assert result.json()['updated']==104
    assert result.json()['unread_count']==0
    assert len(state['notifications']['read_items'])==105
    assert client.get('/api/notifications?unread_only=true').json()['filtered_count']==0


def test_notification_page_query_limits_are_validated():
    client=TestClient(app)
    for query in ['offset=-1','limit=0','limit=101']:
        assert client.get('/api/notifications?'+query).status_code==422
