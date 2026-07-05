import { computed, reactive } from 'vue';

import {
  apiGet,
  apiPost,
  registerApiAuthInvalidationHandler,
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
  id: string;
  username: string;
  email: string;
  display_name: string;
  role: AuthUserRole;
  tenant_id: string;
  expires_at: number | null;
  must_change_password: boolean;
};

type AuthSessionResponse = {
  user: AuthUser;
  session_expires_at: number;
  password_reset: PasswordResetAvailability;
};

type PasswordResetConfirmResult = {
  status: string;
};

type SessionState = {
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
  tenantId: readStorage(TENANT_STORAGE_KEY),
  apiToken: readStorage(API_TOKEN_STORAGE_KEY),
  currentMemberId: readStorage(CURRENT_MEMBER_STORAGE_KEY),
  currentUser: null,
  sessionExpiresAt: 0,
  passwordReset: defaultPasswordReset(),
  loading: false,
  error: '',
});

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
  state.sessionExpiresAt = payload.session_expires_at;
  state.passwordReset = {
    available: payload.password_reset.available,
    reset_id: payload.password_reset.reset_id ?? null,
    detail: payload.password_reset.detail ?? null,
  };
  state.error = '';
  setCurrentMemberId(payload.user.id);
}

function clearAuthSession() {
  state.currentUser = null;
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

function isTenantUnavailableSessionError(error: unknown): error is ApiRequestError {
  if (!(error instanceof Error)) {
    return false;
  }
  const requestError = error as Partial<ApiRequestError>;
  if (requestError.status !== 403) {
    return false;
  }
  return /tenant (is disabled|has expired)/i.test(error.message);
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
    if (state.tenantId) {
      context.tenantId = state.tenantId;
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
        if (isUnauthorizedError(error) || isTenantUnavailableSessionError(error)) {
          clearAuthSession();
        } else if (error instanceof Error) {
          state.error = error.message;
        }
        throw error;
      }
    });
  }

  async function login(tenantId: string, identifier: string, password: string): Promise<AuthSessionResponse> {
    state.error = '';
    return withLoading(async () => {
      try {
        const payload = await apiPost<AuthSessionResponse>('/api/auth/login', {
          tenant_id: tenantId.trim(),
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

  async function changePassword(oldPassword: string, newPassword: string): Promise<AuthSessionResponse> {
    state.error = '';
    return withLoading(async () => {
      try {
        const payload = await apiPost<AuthSessionResponse>('/api/auth/change-password', {
          old_password: oldPassword,
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
    logout,
    changePassword,
    requestPasswordReset,
    confirmPasswordReset,
  };
}
