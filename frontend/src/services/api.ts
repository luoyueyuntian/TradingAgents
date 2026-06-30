export type ApiContext = {
  tenantId?: string;
  apiToken?: string;
  fetchImpl?: typeof fetch;
};

type RequestBody = Record<string, unknown> | unknown[] | string | null;
type ApiErrorDetail = {
  msg?: string;
};

export function buildApiUrl(path: string, context: ApiContext = {}): string {
  const url = new URL(path, window.location.origin);
  const tenantId = context.tenantId?.trim();
  const apiToken = context.apiToken?.trim();
  if (tenantId) {
    url.searchParams.set('tenant_id', tenantId);
  }
  if (apiToken) {
    url.searchParams.set('api_token', apiToken);
  }
  return `${url.pathname}${url.search}`;
}

export async function createApiError(response: Response): Promise<Error> {
  try {
    const payload = await response.json();
    if (payload && typeof payload.detail === 'string') {
      return new Error(payload.detail);
    }
    if (payload && Array.isArray(payload.detail)) {
      return new Error(payload.detail.map((item: ApiErrorDetail | string) => {
        if (typeof item === 'string') {
          return item;
        }
        return item.msg || String(item);
      }).join('; '));
    }
  } catch {
    // Fall back to status text below.
  }
  return new Error(response.statusText || `Request failed with ${response.status}`);
}

function apiHeaders(context: ApiContext): HeadersInit {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };
  const tenantId = context.tenantId?.trim();
  const apiToken = context.apiToken?.trim();
  if (tenantId) {
    headers['X-TradingAgents-Tenant'] = tenantId;
  }
  if (apiToken) {
    headers['X-TradingAgents-Token'] = apiToken;
  }
  return headers;
}

async function apiRequest<T>(
  method: string,
  path: string,
  context: ApiContext = {},
  body?: RequestBody,
): Promise<T> {
  const fetchImpl = context.fetchImpl || fetch;
  const init: RequestInit = {
    headers: apiHeaders(context),
  };
  if (method !== 'GET') {
    init.method = method;
  }
  if (body !== undefined) {
    init.body = typeof body === 'string' ? body : JSON.stringify(body);
  }

  const response = await fetchImpl(buildApiUrl(path, context), init);
  if (!response.ok) {
    throw await createApiError(response);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function apiGet<T = unknown>(path: string, context: ApiContext = {}): Promise<T> {
  return apiRequest<T>('GET', path, context);
}

export function apiPost<T = unknown>(
  path: string,
  body: RequestBody,
  context: ApiContext = {},
): Promise<T> {
  return apiRequest<T>('POST', path, context, body);
}

export function apiPut<T = unknown>(
  path: string,
  body: RequestBody,
  context: ApiContext = {},
): Promise<T> {
  return apiRequest<T>('PUT', path, context, body);
}

export function apiPatch<T = unknown>(
  path: string,
  body: RequestBody,
  context: ApiContext = {},
): Promise<T> {
  return apiRequest<T>('PATCH', path, context, body);
}

export function apiDelete<T = unknown>(path: string, context: ApiContext = {}): Promise<T> {
  return apiRequest<T>('DELETE', path, context);
}
