import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryHistory } from 'vue-router';

const sessionState = {
  currentUser: null as null | {
    id: string;
    username: string;
    email: string;
    display_name: string;
    role: string;
    tenant_id: string;
    expires_at: string | null;
    must_change_password: boolean;
  },
};

const session = {
  state: sessionState,
  mustChangePassword: { get value() { return Boolean(sessionState.currentUser?.must_change_password); } },
  isAdmin: { get value() { return sessionState.currentUser?.role === 'admin'; } },
  loadCurrentUser: vi.fn(),
};

vi.mock('../stores/session', () => ({
  useSession: () => session,
}));

function makeUser(overrides: Partial<NonNullable<typeof sessionState.currentUser>> = {}) {
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

async function loadRouterModule() {
  vi.resetModules();
  return import('./index');
}

describe('router auth guards', () => {
  beforeEach(() => {
    sessionState.currentUser = null;
    session.loadCurrentUser.mockReset();
    session.loadCurrentUser.mockResolvedValue(undefined);
  });

  it('redirects unauthenticated users to /login', async () => {
    const { createAppRouter } = await loadRouterModule();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/analysis');

    expect(router.currentRoute.value.fullPath).toBe('/login');
  });

  it('redirects users who must change password to /change-password', async () => {
    sessionState.currentUser = makeUser({ must_change_password: true });
    const { createAppRouter } = await loadRouterModule();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/runs');

    expect(router.currentRoute.value.fullPath).toBe('/change-password');
  });

  it('blocks non-admin users from navigating to /users', async () => {
    sessionState.currentUser = makeUser({ role: 'analyst' });
    const { createAppRouter } = await loadRouterModule();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/users');

    expect(router.currentRoute.value.fullPath).toBe('/');
  });

  it('allows admin users to navigate to /users', async () => {
    sessionState.currentUser = makeUser({ role: 'admin' });
    const { createAppRouter } = await loadRouterModule();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/users');

    expect(router.currentRoute.value.fullPath).toBe('/users');
  });
});
