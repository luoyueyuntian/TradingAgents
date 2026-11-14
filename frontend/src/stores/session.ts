import { computed, reactive } from 'vue';

import {
  apiGet,
  apiPost,
  registerApiAuthInvalidationHandler,
  registerSessionTenantContext,
  type ApiContext,
  type ApiRequestError,
} from '../services/api';

const TENANT_STORAGE_KEY = 'tradingagents.tenantId';
const API_TOKEN_STORAGE_KEY = 'tradingagents.apiToken';
const CURRENT_MEMBER_STORAGE_KEY = 'tradingagents.currentMemberId';

type AuthUserRole = 'viewer' | 'analyst' | 'admin' | string;

type PasswordResetAvailability = {
  available: boolean;
  reset_id: string | null;
  detail: string | null;
};

type AuthUser = {
  account_id?: string;
  member_id?: string | null;
  id: string;
  username: string;
  email: string;
  display_name: string;
  role: AuthUserRole;
  tenant_id: string;
  expires_at: number | null;
  must_change_password: boolean;
};

export type TenantMembership = {
  tenant_id: string;
  display_name: string;
  role: string;
  member_id: string;
};

type AuthSessionResponse = {
  tenants?: TenantMembership[];
  user: AuthUser;
  session_expires_at: number;
  password_reset: PasswordResetAvailability;
};

type PasswordResetConfirmResult = {
  status: string;
};

type SessionState = {
  tenants: TenantMembership[];
  tenantId: string;
  apiToken: string;
  currentMemberId: string;
  currentUser: AuthUser | null;
  sessionExpiresAt: number;
  passwordReset: PasswordResetAvailability;
  loading: boolean;
  error: string;
};

function readStorage(key: string): string {
  if (typeof window === 'undefined') {
    return '';
  }
  return window.localStorage.getItem(key) || '';
}

function writeStorage(key: string, value: string): void {
  if (typeof window === 'undefined') {
    return;
  }
  if (value) {
    window.localStorage.setItem(key, value);
  } else {
    window.localStorage.removeItem(key);
  }
}

function defaultPasswordReset(): PasswordResetAvailability {
  return {
    available: false,
    reset_id: null,
    detail: null,
  };
}

const state = reactive<SessionState>({
  tenants: [],
  tenantId: readStorage(TENANT_STORAGE_KEY),
  apiToken: readStorage(API_TOKEN_STORAGE_KEY),
  currentMemberId: readStorage(CURRENT_MEMBER_STORAGE_KEY),
  currentUser: null,
  sessionExpiresAt: 0,
  passwordReset: defaultPasswordReset(),
  loading: false,
  error: '',
});

const SESSION_SWITCH_KEY = 'tradingagents.sessionSwitch';
registerSessionTenantContext(
  () => state.currentUser ? state.currentUser.tenant_id : undefined,
  () => window.location.assign('/'),
);
window.addEventListener('storage', (event) => {
  if (event.key === SESSION_SWITCH_KEY && state.currentUser) window.location.assign('/');
});
async function revalidateTabTenant(): Promise<void> {
  if (!state.currentUser) return;
  const expectedTenant = state.currentUser.tenant_id;
  try {
    const payload = await apiGet<AuthSessionResponse>('/api/auth/me', {});
    if (payload.user.tenant_id !== expectedTenant) window.location.assign('/');
  } catch {
    // Authentication failures are handled by the API invalidation handler.
  }
}
window.addEventListener('focus', () => { void revalidateTabTenant(); });
window.addEventListener('pageshow', () => { void revalidateTabTenant(); });


let authInvalidationHandlerRegistered = false;

function setTenantId(value: string) {
  state.tenantId = value.trim();
  writeStorage(TENANT_STORAGE_KEY, state.tenantId);
}

function setApiToken(value: string) {
  state.apiToken = value.trim();
  writeStorage(API_TOKEN_STORAGE_KEY, state.apiToken);
}

function setCurrentMemberId(value: string) {
  state.currentMemberId = value.trim();
  writeStorage(CURRENT_MEMBER_STORAGE_KEY, state.currentMemberId);
}

function clearCurrentMemberId() {
  setCurrentMemberId('');
}

function applyAuthSession(payload: AuthSessionResponse) {
  state.currentUser = payload.user;
  state.tenants = payload.tenants ?? [];
  state.sessionExpiresAt = payload.session_expires_at;
  state.passwordReset = {
    available: payload.password_reset.available,
    reset_id: payload.password_reset.reset_id ?? null,
    detail: payload.password_reset.detail ?? null,
  };
  state.error = '';
  setCurrentMemberId(payload.user.member_id === null ? '' : payload.user.member_id ?? payload.user.id);
}

function clearAuthSession() {
  state.currentUser = null;
  state.tenants = [];
  state.sessionExpiresAt = 0;
  state.passwordReset = defaultPasswordReset();
  state.error = '';
  clearCurrentMemberId();
}

function ensureAuthInvalidationHandlerRegistered() {
  if (authInvalidationHandlerRegistered) {
    return;
  }
  registerApiAuthInvalidationHandler(() => {
    clearAuthSession();
  });
  authInvalidationHandlerRegistered = true;
}

function isUnauthorizedError(error: unknown): error is ApiRequestError {
  if (!(error instanceof Error)) {
    return false;
  }
  const requestError = error as Partial<ApiRequestError>;
  return requestError.status === 401 || /unauthorized/i.test(error.message);
}

async function withLoading<T>(operation: () => Promise<T>): Promise<T> {
  state.loading = true;
  try {
    return await operation();
  } finally {
    state.loading = false;
  }
}

export function useSession() {
  ensureAuthInvalidationHandlerRegistered();

  const authApiContext: ApiContext = {};
  const apiContext = computed<ApiContext>(() => {
    const context: ApiContext = {};
    const tenantId = state.currentUser ? state.currentUser.tenant_id : state.tenantId;
    if (tenantId) {
      context.tenantId = tenantId;
    }
    if (state.apiToken) {
      context.apiToken = state.apiToken;
    }
    return context;
  });

  async function loadCurrentUser(): Promise<AuthSessionResponse> {
    state.error = '';
    return withLoading(async () => {
      try {
        const payload = await apiGet<AuthSessionResponse>('/api/auth/me', authApiContext);
        applyAuthSession(payload);
        return payload;
      } catch (error) {
        if (isUnauthorizedError(error)) {
          clearAuthSession();
        } else if (error instanceof Error) {
          state.error = error.message;
        }
        throw error;
      }
    });
  }

  async function login(identifier: string, password: string): Promise<AuthSessionResponse> {
    state.error = '';
    return withLoading(async () => {
      try {
        const payload = await apiPost<AuthSessionResponse>('/api/auth/login', {
          identifier: identifier.trim(),
          password,
        }, authApiContext);
        applyAuthSession(payload);
        return payload;
      } catch (error) {
        if (error instanceof Error) {
          state.error = error.message;
        }
        throw error;
      }
    });
  }

  async function switchTenant(tenantId: string): Promise<AuthSessionResponse> {
    state.error = '';
    return withLoading(async () => {
      try {
        const payload = await apiPost<AuthSessionResponse>('/api/auth/switch-tenant', {
          tenant_id: tenantId,
        }, authApiContext);
        applyAuthSession(payload);
        writeStorage(SESSION_SWITCH_KEY, `${Date.now()}:${Math.random()}`);
        return payload;
      } catch (error) {
        state.error = error instanceof Error ? error.message : String(error);
        throw error;
      }
    });
  }

  async function logout(): Promise<void> {
    state.error = '';
    return withLoading(async () => {
      try {
        await apiPost('/api/auth/logout', {}, authApiContext);
      } finally {
        clearAuthSession();
      }
    });
  }

  async function changePassword(newPassword: string): Promise<AuthSessionResponse> {
    state.error = '';
    return withLoading(async () => {
      try {
        const payload = await apiPost<AuthSessionResponse>('/api/auth/change-password', {
          new_password: newPassword,
        }, authApiContext);
        applyAuthSession(payload);
        return payload;
      } catch (error) {
        if (error instanceof Error) {
          state.error = error.message;
        }
        throw error;
      }
    });
  }

  async function requestPasswordReset(email: string): Promise<PasswordResetAvailability> {
    state.error = '';
    return withLoading(async () => {
      const payload = await apiPost<PasswordResetAvailability>('/api/auth/password-reset/request', {
        email: email.trim(),
      }, authApiContext);
      state.passwordReset = {
        available: payload.available,
        reset_id: payload.reset_id ?? null,
        detail: payload.detail ?? null,
      };
      return payload;
    });
  }

  async function confirmPasswordReset(
    resetId: string,
    code: string,
    newPassword: string,
  ): Promise<PasswordResetConfirmResult> {
    state.error = '';
    return withLoading(async () => apiPost<PasswordResetConfirmResult>('/api/auth/password-reset/confirm', {
      reset_id: resetId.trim(),
      code: code.trim(),
      new_password: newPassword,
    }, authApiContext));
  }

  const mustChangePassword = computed(() => Boolean(state.currentUser?.must_change_password));
  const isAdmin = computed(() => state.currentUser?.role === 'admin');
  const canWrite = computed(() => {
    const role = state.currentUser?.role;
    return role === 'analyst' || role === 'admin';
  });
  const canAnalyze = computed(() => {
    const role = state.currentUser?.role;
    return role === 'analyst' || role === 'admin';
  });

  return {
    state,
    apiContext,
    mustChangePassword,
    isAdmin,
    canWrite,
    canAnalyze,
    setTenantId,
    setApiToken,
    setCurrentMemberId,
    loadCurrentUser,
    login,
    switchTenant,
    logout,
    changePassword,
    requestPasswordReset,
    confirmPasswordReset,
  };
}
