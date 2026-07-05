import { describe, expect, it, vi } from 'vitest';

import { apiGet, buildApiUrl, createApiError, registerApiAuthInvalidationHandler } from './api';

describe('api service', () => {
  it('adds tenant and token query parameters for browser APIs that cannot send headers', () => {
    const url = buildApiUrl('/api/runs', {
      tenantId: 'research-desk',
      apiToken: 'secret-token',
    });

    expect(url).toBe('/api/runs?tenant_id=research-desk&api_token=secret-token');
  });

  it('preserves existing query parameters when appending tenant context', () => {
    const url = buildApiUrl('/api/runs?status=completed', {
      tenantId: 'desk a',
      apiToken: '',
    });

    expect(url).toBe('/api/runs?status=completed&tenant_id=desk+a');
  });

  it('turns FastAPI JSON errors into readable Error objects', async () => {
    const response = new Response(JSON.stringify({ detail: 'Invalid ticker' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' },
    });

    const error = await createApiError(response);

    expect(error.message).toBe('Invalid ticker');
  });

  it('formats FastAPI validation error arrays', async () => {
    const response = new Response(JSON.stringify({ detail: [{ msg: 'Ticker is required' }, { msg: 'Date is invalid' }] }), {
      status: 422,
      headers: { 'Content-Type': 'application/json' },
    });

    const error = await createApiError(response);

    expect(error.message).toBe('Ticker is required; Date is invalid');
  });

  it('preserves structured detail objects for downstream conflict handling', async () => {
    const response = new Response(JSON.stringify({
      detail: {
        code: 'ticker_active_run_exists',
        message: 'AAPL already has an active analysis run.',
        active_run_id: 'run-active',
        active_run_status: 'running',
      },
    }), {
      status: 409,
      headers: { 'Content-Type': 'application/json' },
    });

    const error = await createApiError(response);

    expect(error.message).toBe('AAPL already has an active analysis run.');
    expect(error.status).toBe(409);
    expect((error as Error & { detail?: Record<string, unknown> }).detail).toEqual({
      code: 'ticker_active_run_exists',
      message: 'AAPL already has an active analysis run.',
      active_run_id: 'run-active',
      active_run_status: 'running',
    });
  });

  it('attaches the HTTP status to api request errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Unauthorized' }), {
        status: 401,
        statusText: 'Unauthorized',
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await expect(apiGet('/api/auth/me', { fetchImpl: fetchMock })).rejects.toMatchObject({
      message: 'Unauthorized',
      status: 401,
    });
  });

  it.each([
    'Tenant is disabled',
    'Tenant has expired',
  ])('runs auth invalidation handlers for own-session tenant-state 403 responses: %s', async (detail) => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail }), {
        status: 403,
        statusText: 'Forbidden',
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const invalidationHandler = vi.fn();
    const unregister = registerApiAuthInvalidationHandler(invalidationHandler);

    try {
      await expect(apiGet('/api/auth/me', { fetchImpl: fetchMock })).rejects.toMatchObject({
        message: detail,
        status: 403,
      });
      expect(invalidationHandler).toHaveBeenCalledTimes(1);
    } finally {
      unregister();
    }
  });

  it.each([
    'Tenant is disabled',
    'Tenant has expired',
  ])('does not run auth invalidation handlers for cross-tenant admin tenant-state 403 responses: %s', async (detail) => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail }), {
        status: 403,
        statusText: 'Forbidden',
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const invalidationHandler = vi.fn();
    const unregister = registerApiAuthInvalidationHandler(invalidationHandler);

    try {
      await expect(apiGet('/api/admin/tenants/tenant-b/members', { fetchImpl: fetchMock })).rejects.toMatchObject({
        message: detail,
        status: 403,
      });
      expect(invalidationHandler).not.toHaveBeenCalled();
    } finally {
      unregister();
    }
  });

  it('does not run auth invalidation handlers for unrelated 403 responses', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: 'Forbidden' }), {
        status: 403,
        statusText: 'Forbidden',
        headers: { 'Content-Type': 'application/json' },
      }),
    );
    const invalidationHandler = vi.fn();
    const unregister = registerApiAuthInvalidationHandler(invalidationHandler);

    try {
      await expect(apiGet('/api/runs', { fetchImpl: fetchMock })).rejects.toMatchObject({
        message: 'Forbidden',
        status: 403,
      });
      expect(invalidationHandler).not.toHaveBeenCalled();
    } finally {
      unregister();
    }
  });

  it('sends tenant and token headers for JSON fetch requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ run_id: 'run-1' }]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    const result = await apiGet('/api/runs', {
      tenantId: 'alpha',
      apiToken: 'token',
      fetchImpl: fetchMock,
    });

    expect(result).toEqual([{ run_id: 'run-1' }]);
    expect(fetchMock).toHaveBeenCalledWith('/api/runs?tenant_id=alpha&api_token=token', {
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
        'X-TradingAgents-Tenant': 'alpha',
        'X-TradingAgents-Token': 'token',
      },
    });
  });

  it('sends same-origin credentials by default for cookie-backed session requests', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([{ run_id: 'run-1' }]), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      }),
    );

    await apiGet('/api/runs', {
      fetchImpl: fetchMock,
    });

    expect(fetchMock).toHaveBeenCalledWith('/api/runs', {
      credentials: 'same-origin',
      headers: {
        'Content-Type': 'application/json',
      },
    });
  });
});
