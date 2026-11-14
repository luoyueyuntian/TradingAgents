export type ApiContext = {
  tenantId?: string;
  apiToken?: string;
  fetchImpl?: typeof fetch;
};

export type ApiRequestError = Error & {
  status: number;
  detail?: unknown;
};

type ApiAuthInvalidationHandler = () => void;

type RequestBody = Record<string, unknown> | unknown[] | string | null;
type ApiErrorDetail = {
  msg?: string;
};

const authInvalidationHandlers = new Set<ApiAuthInvalidationHandler>();

let sessionTenantProvider: () => string | undefined = () => undefined;
let tenantContextHandler: () => void = () => undefined;
export function registerSessionTenantContext(provider: () => string | undefined, handler: () => void): void {
  sessionTenantProvider = provider;
  tenantContextHandler = handler;
}

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

function withApiStatus(error: Error, response: Response): ApiRequestError {
  return Object.assign(error, { status: response.status });
}

function shouldInvalidateAuth(error: ApiRequestError, path: string): boolean {
  // Tenant availability does not invalidate the account: the user can switch tenants.
  return error.status === 401 && path !== '/api/auth/login';
}

function notifyAuthInvalidationHandlers(error: ApiRequestError, path: string): void {
  if (!shouldInvalidateAuth(error, path)) {
    return;
  }
  authInvalidationHandlers.forEach((handler) => handler());
}

export function registerApiAuthInvalidationHandler(handler: ApiAuthInvalidationHandler): () => void {
  authInvalidationHandlers.add(handler);
  return () => {
    authInvalidationHandlers.delete(handler);
  };
}

export async function createApiError(response: Response): Promise<ApiRequestError> {
  try {
    const payload = await response.json();
    if (payload && typeof payload.detail === 'string') {
      return withApiStatus(new Error(payload.detail), response);
    }
    if (payload && payload.detail && typeof payload.detail === 'object' && !Array.isArray(payload.detail)) {
      const detail = payload.detail as Record<string, unknown>;
      const message = typeof detail.message === 'string' && detail.message
        ? detail.message
        : response.statusText || `Request failed with ${response.status}`;
      return Object.assign(withApiStatus(new Error(message), response), { detail });
    }
    if (payload && Array.isArray(payload.detail)) {
      return withApiStatus(new Error(payload.detail.map((item: ApiErrorDetail | string) => {
        if (typeof item === 'string') {
          return item;
        }
        return item.msg || String(item);
      }).join('; ')), response);
    }
  } catch {
    // Fall back to status text below.
  }
  return withApiStatus(new Error(response.statusText || `Request failed with ${response.status}`), response);
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
  const sessionTenant = path.startsWith('/api/auth/') ? undefined : sessionTenantProvider();
  const fetchImpl = context.fetchImpl || fetch;
  const init: RequestInit = {
    credentials: 'same-origin',
    headers: apiHeaders(context),
  };
  if (sessionTenant !== undefined) {
    (init.headers as Record<string, string>)['X-TradingAgents-Session-Tenant'] = sessionTenant;
  }
  if (method !== 'GET') {
    init.method = method;
  }
  if (body !== undefined) {
    init.body = typeof body === 'string' ? body : JSON.stringify(body);
  }

  const response = await fetchImpl(buildApiUrl(path, context), init);
  if (!response.ok) {
    const error = await createApiError(response);
    if (error.status === 409 && sessionTenant !== undefined && error.message === 'Tenant context changed; reload required') {
      tenantContextHandler();
    }
    notifyAuthInvalidationHandlers(error, path);
    throw error;
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
