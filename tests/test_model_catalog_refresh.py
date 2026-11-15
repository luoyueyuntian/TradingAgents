import asyncio

import pytest

from web import model_catalog_refresh as catalog


def test_refresh_replaces_all_models_and_preserves_failed_provider(tmp_path, monkeypatch):
    monkeypatch.setattr(catalog, 'MODEL_OPTIONS', {'openai': {}, 'google': {}})
    catalog.save_cache(tmp_path, {'openai': [['Old', 'old']], 'google': [['Cached', 'cached']]})
    def fetch(provider, settings):
        if provider == 'google':
            raise ValueError('API key not configured')
        return [('New', 'new'), ('Second', 'second')]
    monkeypatch.setattr(catalog, 'fetch_models', fetch)
    models, errors = asyncio.run(catalog.refresh_catalogs(tmp_path, {}))
    assert models == {'openai': [['New', 'new'], ['Second', 'second']], 'google': [['Cached', 'cached']], 'openrouter': [['New', 'new'], ['Second', 'second']]}
    assert errors == {'google': 'API key not configured'}
    assert catalog.load_cache(tmp_path) == models


def test_fetch_reads_every_page_and_deduplicates(monkeypatch):
    pages = iter([
        {'data': [{'id': 'new'}, {'id': 'second'}], 'has_more': True, 'last_id': 'second'},
        {'data': [{'id': 'second'}, {'id': 'third'}], 'has_more': False},
    ])
    calls = []
    def get(url, **kwargs):
        calls.append((url, kwargs))
        class Response:
            status_code = 200
            def json(self): return next(pages)
        return Response()
    monkeypatch.setattr(catalog.requests, 'get', get)
    result = catalog.fetch_models('anthropic', {'api_keys': {'anthropic': 'test-key'}})
    assert [item[1] for item in result] == ['new', 'second', 'third']
    assert calls[1][1]['params']['after_id'] == 'second'


def test_partial_page_failure_does_not_return_incomplete_catalog(monkeypatch):
    def get(url, **kwargs):
        class Response:
            status_code = 200 if not kwargs['params'] else 403
            def json(self): return {'data': [{'id': 'first'}], 'has_more': True, 'last_id': 'first'}
        return Response()
    monkeypatch.setattr(catalog.requests, 'get', get)
    with pytest.raises(ValueError, match='403'):
        catalog.fetch_models('anthropic', {'api_keys': {'anthropic': 'test'}})


def test_google_reads_all_pages_and_only_offers_generation_models(monkeypatch):
    pages = iter([
        {'models': [{'name': 'models/gemini-new', 'supportedGenerationMethods': ['generateContent']}], 'nextPageToken': 'next'},
        {'models': [{'name': 'models/embedding', 'supportedGenerationMethods': ['embedContent']}, {'name': 'models/gemini-other', 'supportedGenerationMethods': ['generateContent']}]},
    ])
    calls = []
    def get(url, **kwargs):
        calls.append(kwargs)
        class Response:
            status_code = 200
            def json(self): return next(pages)
        return Response()
    monkeypatch.setattr(catalog.requests, 'get', get)
    result = catalog.fetch_models('google', {'api_keys': {'google': 'tenant-key'}})
    assert [value for _, value in result] == ['gemini-new', 'gemini-other']
    assert calls[1]['params'] == {'pageToken': 'next'}
    assert calls[0]['headers']['x-goog-api-key'] == 'tenant-key'


def test_provider_refresh_route_uses_tenant_settings_and_cached_catalog(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from web import routes
    from web.app import app
    from web.user_store import UserStore
    monkeypatch.setenv('TRADINGAGENTS_WEB_STATE_DIR', str(tmp_path))
    store = UserStore(tmp_path / 'auth.db')
    store.create_tenant('tenant-a', display_name='A')
    monkeypatch.setattr(routes, 'load_settings', lambda path=None: {'api_keys': {'openai': 'tenant-key'}})
    seen = []
    async def refresh(root, settings):
        seen.append((root, settings))
        catalog.save_cache(root, {'openai': [['New', 'new']]})
        return {'openai': [['New', 'new']]}, {'google': 'Missing key'}
    monkeypatch.setattr(routes, 'refresh_catalogs', refresh)
    client = TestClient(app)
    result = client.post('/api/settings/models/refresh?tenant_id=tenant-a')
    assert result.status_code == 200
    by_provider = {p['provider']: p for p in result.json()}
    assert by_provider['openai']['quick_models'] == [{'label': 'New', 'value': 'new'}, {'label': 'Custom model ID', 'value': 'custom'}]
    assert by_provider['google']['model_refresh_error'] == 'Missing key'
    assert seen[0][0] == tmp_path / 'tenants/tenant-a'
    assert seen[0][1]['api_keys']['openai'] == 'tenant-key'
    read = client.get('/api/providers?tenant_id=tenant-a')
    assert next(p for p in read.json() if p['provider']=='openai')['quick_models'][0]['value'] == 'new'
    other = client.get('/api/providers')
    assert next(p for p in other.json() if p['provider']=='openai')['quick_models'][0]['value'] != 'new'
