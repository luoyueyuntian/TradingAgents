"""Tenant-scoped live model catalogs. Never persist credentials or partial pages."""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
import time
from pathlib import Path

import requests

from tradingagents.llm_clients.model_catalog import MODEL_OPTIONS
from tradingagents.llm_clients.openai_client import OPENAI_COMPATIBLE_PROVIDERS
from tradingagents.settings import PROVIDER_API_KEY_MAP


def load_cache(root: Path) -> dict:
    try:
        value = json.loads((root / 'model-catalogs.json').read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_cache(root: Path, models: dict) -> None:
    root.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=root, prefix='.model-catalogs-')
    try:
        with os.fdopen(fd, 'w') as f:
            json.dump(models, f)
        os.replace(name, root / 'model-catalogs.json')
    finally:
        Path(name).unlink(missing_ok=True)


def fetch_models(provider: str, settings: dict) -> list[tuple[str, str]]:
    spec = OPENAI_COMPATIBLE_PROVIDERS.get(provider)
    if provider in {'bedrock', 'chatgpt'}:
        raise ValueError('This provider requires a separate account/session; live listing is unavailable here')
    env = PROVIDER_API_KEY_MAP.get(provider)
    key = settings.get('api_keys', {}).get(provider) or (os.getenv(env, '') if env else '')
    if key == '***':
        key = ''
    if not key and provider != 'openrouter' and not (spec and spec.key_optional):
        raise ValueError('API key not configured; save the provider key first')
    llm = settings.get('llm', {})
    base = (llm.get('backend_url') if llm.get('provider') == provider else None)
    if provider == 'anthropic':
        base = base or 'https://api.anthropic.com/v1'
        headers = {'x-api-key': key, 'anthropic-version': '2023-06-01'}
    elif provider == 'google':
        base = base or 'https://generativelanguage.googleapis.com/v1beta'
        headers = {'x-goog-api-key': key}
    elif spec:
        base = base or (os.getenv(spec.base_url_env) if spec.base_url_env else None) or spec.base_url
        headers = {'Authorization': f'Bearer {key}'} if key else {}
        if provider == 'openai':
            base = base or 'https://api.openai.com/v1'
        if provider == 'deepseek' and base and base.rstrip('/') == 'https://api.deepseek.com':
            base += '/v1'
    else:
        raise ValueError('Live model listing is unavailable for this provider')
    if not base:
        raise ValueError('Backend URL not configured')
    url = base.rstrip('/') + '/models'
    params: dict = {}
    models: dict[str, str] = {}
    cursors: set[str] = set()
    deadline = time.monotonic() + 25
    for _ in range(100):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ValueError('Model listing timed out before all pages were read')
        try:
            response = requests.get(url, headers=headers, params=params, timeout=min(8, remaining), allow_redirects=False)
            if response.status_code != 200:
                raise ValueError(f'Model listing returned HTTP {response.status_code}')
            body = response.json()
        except requests.RequestException:
            raise ValueError('Unable to connect to model listing endpoint') from None
        items = body.get('models' if provider == 'google' else 'data')
        if not isinstance(items, list):
            raise ValueError('Invalid model listing response')
        for item in items:
            if not isinstance(item, dict):
                continue
            if provider == 'google' and 'generateContent' not in item.get('supportedGenerationMethods', []):
                continue
            model_id = item.get('name', '').removeprefix('models/') if provider == 'google' else item.get('id')
            if isinstance(model_id, str) and model_id and model_id != 'custom':
                models[model_id] = item.get('displayName') or item.get('display_name') or item.get('name') or model_id
        cursor = body.get('nextPageToken') if provider == 'google' else (body.get('last_id') if body.get('has_more') else None)
        if not cursor and body.get('has_more'):
            raise ValueError('Incomplete pagination response')
        if not cursor:
            if not models:
                raise ValueError('Provider returned no usable models')
            return [(label, value) for value, label in models.items()]
        if cursor in cursors:
            raise ValueError('Model listing repeated a page')
        cursors.add(cursor)
        params = {'pageToken' if provider == 'google' else 'after_id': cursor}
    raise ValueError('Model listing exceeded pagination limit')


async def refresh_catalogs(root: Path, settings: dict) -> tuple[dict, dict]:
    models = load_cache(root)
    errors = {}
    semaphore = asyncio.Semaphore(8)

    async def refresh(provider):
        async with semaphore:
            try:
                items = await asyncio.to_thread(fetch_models, provider, settings)
                models[provider] = [[label, value] for label, value in items]
            except ValueError as exc:
                errors[provider] = str(exc)
            except Exception:
                errors[provider] = 'Unable to refresh model list'
    await asyncio.gather(*(refresh(provider) for provider in dict.fromkeys([*MODEL_OPTIONS, 'openrouter'])))
    save_cache(root, models)
    return models, errors
