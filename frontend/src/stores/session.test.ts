import { beforeEach, describe, expect, it, vi } from 'vitest';

const apiGetMock = vi.fn();
const apiPostMock = vi.fn();

vi.mock('../services/api', () => ({
  apiGet: apiGetMock,
  apiPost: apiPostMock,
}));

type AuthUser = {
  id: string;
  username: string;
  email: string;
  display_name: string;
  role: string;
  tenant_id: string;
  expires_at: string | null;
  must_change_password: boolean;
};

type AuthSessionResponse = {
  user: AuthUser;
  session_expires_at: string;
  password_reset: {
    available: boolean;
    reset_id?: string | null;
    detail?: string | null;
  };
};

function makeUser(overrides: Partial<AuthUser> = {}): AuthUser {
  return {
    id: 'user-1',
    username: 'alice',
    email: 'alice@example.com',
    display_name: 'Alice Analyst',
    role: 'analyst',
    tenant_id: 'tenant-a',
    expires_at: null,
    must_change_password: false,
    ...overrides,
  };
}

function makeAuthResponse(overrides: Partial<AuthSessionResponse> = {}): AuthSessionResponse {
  const userOverrides = overrides.user ?? {};
  const passwordResetOverrides = overrides.password_reset ?? {};
  const { user: _user, password_reset: _passwordReset, ...restOverrides } = overrides;
  return {
    user: makeUser(userOverrides),
    session_expires_at: '2026-07-03T00:00:00Z',
    password_reset: {
      available: true,
      reset_id: null,
      detail: null,
      ...passwordResetOverrides,
    },
    ...restOverrides,
  };
}

async function loadSessionModule() {
  vi.resetModules();
  return import('./session');
}

describe('session store', () => {
  beforeEach(() => {
    apiGetMock.mockReset();
    apiPostMock.mockReset();
    window.localStorage.clear();
  });

  it('loads the current user through /api/auth/me and stores session metadata', async () => {
    apiGetMock.mockResolvedValue(makeAuthResponse({
      user: makeUser({ must_change_password: true, role: 'admin' }),
    }));
    const { useSession } = await loadSessionModule();

    const session = useSession();
    await session.loadCurrentUser();

    expect(apiGetMock).toHaveBeenCalledWith('/api/auth/me', {});
    expect(session.state.currentUser?.username).toBe('alice');
    expect(session.state.sessionExpiresAt).toBe('2026-07-03T00:00:00Z');
    expect(session.state.passwordReset.available).toBe(true);
    expect(session.mustChangePassword.value).toBe(true);
    expect(session.isAdmin.value).toBe(true);
    expect(session.canWrite.value).toBe(true);
    expect(session.canAnalyze.value).toBe(true);
    expect(session.state.loading).toBe(false);
    expect(session.state.error).toBe('');
  });

  it('keeps auth session calls isolated from legacy tenant and token context', async () => {
    apiGetMock.mockResolvedValue(makeAuthResponse());
    apiPostMock
      .mockResolvedValueOnce(makeAuthResponse())
      .mockResolvedValueOnce({ status: 'ok' })
      .mockResolvedValueOnce(makeAuthResponse())
      .mockResolvedValueOnce({ available: true, reset_id: 'reset-123', detail: null })
      .mockResolvedValueOnce({ status: 'ok' });
    const { useSession } = await loadSessionModule();

    const session = useSession();
    session.setTenantId('operator-tenant');
    session.setApiToken('operator-token');

    await session.loadCurrentUser();
    await session.login('alice', 'StrongPass123!');
    await session.logout();
    await session.changePassword('OldPass123!', 'NewPass456!');
    await session.requestPasswordReset('alice@example.com');
    await session.confirmPasswordReset('reset-123', '123456', 'NewPass456!');

    expect(apiGetMock).toHaveBeenCalledWith('/api/auth/me', {});
    expect(apiPostMock).toHaveBeenNthCalledWith(1, '/api/auth/login', {
      identifier: 'alice',
      password: 'StrongPass123!',
    }, {});
    expect(apiPostMock).toHaveBeenNthCalledWith(2, '/api/auth/logout', {}, {});
    expect(apiPostMock).toHaveBeenNthCalledWith(3, '/api/auth/change-password', {
      old_password: 'OldPass123!',
      new_password: 'NewPass456!',
    }, {});
    expect(apiPostMock).toHaveBeenNthCalledWith(4, '/api/auth/password-reset/request', {
      email: 'alice@example.com',
    }, {});
    expect(apiPostMock).toHaveBeenNthCalledWith(5, '/api/auth/password-reset/confirm', {
      reset_id: 'reset-123',
      code: '123456',
      new_password: 'NewPass456!',
    }, {});
  });

  it('clears the current user on unauthorized loadCurrentUser failures', async () => {
    apiGetMock.mockRejectedValue(Object.assign(new Error('Unauthorized'), { status: 401 }));
    const { useSession } = await loadSessionModule();

    const session = useSession();
    session.state.currentUser = makeAuthResponse().user;
    session.state.sessionExpiresAt = '2026-07-03T00:00:00Z';

    await expect(session.loadCurrentUser()).rejects.toThrow('Unauthorized');
    expect(session.state.currentUser).toBeNull();
    expect(session.state.sessionExpiresAt).toBe('');
    expect(session.state.error).toBe('');
  });

  it('logs in and stores returned user session data', async () => {
    apiPostMock.mockResolvedValue(makeAuthResponse());
    const { useSession } = await loadSessionModule();

    const session = useSession();
    await session.login(' alice ', 'StrongPass123!');

    expect(apiPostMock).toHaveBeenCalledWith('/api/auth/login', {
      identifier: 'alice',
      password: 'StrongPass123!',
    }, {});
    expect(session.state.currentUser?.username).toBe('alice');
  });

  it('logs out and clears current user and session data', async () => {
    apiPostMock.mockResolvedValue({ status: 'ok' });
    const { useSession } = await loadSessionModule();

    const session = useSession();
    session.state.currentUser = makeAuthResponse().user;
    session.state.sessionExpiresAt = '2026-07-03T00:00:00Z';
    session.state.passwordReset = { available: true, reset_id: 'reset-1', detail: null };

    await session.logout();

    expect(apiPostMock).toHaveBeenCalledWith('/api/auth/logout', {}, {});
    expect(session.state.currentUser).toBeNull();
    expect(session.state.sessionExpiresAt).toBe('');
    expect(session.state.passwordReset).toEqual({ available: false, reset_id: null, detail: null });
  });

  it('changes password and refreshes the current user session response', async () => {
    apiPostMock.mockResolvedValue(makeAuthResponse({
      user: makeUser({ must_change_password: false }),
    }));
    const { useSession } = await loadSessionModule();

    const session = useSession();
    await session.changePassword('OldPass123!', 'NewPass456!');

    expect(apiPostMock).toHaveBeenCalledWith('/api/auth/change-password', {
      old_password: 'OldPass123!',
      new_password: 'NewPass456!',
    }, {});
    expect(session.mustChangePassword.value).toBe(false);
  });

  it('forwards password reset request and confirm responses without storing secrets', async () => {
    apiPostMock
      .mockResolvedValueOnce({ available: true, reset_id: 'reset-123', detail: null })
      .mockResolvedValueOnce({ status: 'ok' });
    const { useSession } = await loadSessionModule();

    const session = useSession();
    const requestResult = await session.requestPasswordReset('alice@example.com');
    const confirmResult = await session.confirmPasswordReset('reset-123', '123456', 'NewPass456!');

    expect(apiPostMock).toHaveBeenNthCalledWith(1, '/api/auth/password-reset/request', {
      email: 'alice@example.com',
    }, {});
    expect(apiPostMock).toHaveBeenNthCalledWith(2, '/api/auth/password-reset/confirm', {
      reset_id: 'reset-123',
      code: '123456',
      new_password: 'NewPass456!',
    }, {});
    expect(requestResult).toEqual({ available: true, reset_id: 'reset-123', detail: null });
    expect(confirmResult).toEqual({ status: 'ok' });
    expect(session.state.currentUser).toBeNull();
    expect(window.localStorage.getItem('tradingagents.currentMemberId')).toBeNull();
  });

  it('stores password reset availability responses on the session state', async () => {
    apiPostMock.mockResolvedValue({ available: true, reset_id: 'reset-123', detail: null });
    const { useSession } = await loadSessionModule();

    const session = useSession();
    await session.requestPasswordReset('alice@example.com');

    expect(session.state.passwordReset).toEqual({
      available: true,
      reset_id: 'reset-123',
      detail: null,
    });
  });

  it('supports role helpers for viewer, analyst, and admin', async () => {
    const { useSession } = await loadSessionModule();
    const session = useSession();

    session.state.currentUser = makeAuthResponse({ user: makeUser({ role: 'viewer' }) }).user;
    expect(session.isAdmin.value).toBe(false);
    expect(session.canWrite.value).toBe(false);
    expect(session.canAnalyze.value).toBe(false);

    session.state.currentUser = makeAuthResponse({ user: makeUser({ role: 'analyst' }) }).user;
    expect(session.canWrite.value).toBe(true);
    expect(session.canAnalyze.value).toBe(true);

    session.state.currentUser = makeAuthResponse({ user: makeUser({ role: 'admin' }) }).user;
    expect(session.isAdmin.value).toBe(true);
    expect(session.canWrite.value).toBe(true);
    expect(session.canAnalyze.value).toBe(true);
  });
});
