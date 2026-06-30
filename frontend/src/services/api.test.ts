import { describe, expect, it, vi } from 'vitest';

import { apiGet, buildApiUrl, createApiError } from './api';

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
      headers: {
        'Content-Type': 'application/json',
        'X-TradingAgents-Tenant': 'alpha',
        'X-TradingAgents-Token': 'token',
      },
    });
  });
});
