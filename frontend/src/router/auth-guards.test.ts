import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryHistory } from 'vue-router';

vi.mock('../pages/TenantsPage.vue', () => ({ default: { name: 'TenantsPage' } }), { virtual: true });
vi.mock('../pages/TenantDetailPage.vue', () => ({ default: { name: 'TenantDetailPage' } }), { virtual: true });

const sessionState = {
  loading: false,
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
    sessionState.loading = false;
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

  it('strips the deployed SPA base from the initial browser location', async () => {
    window.history.replaceState({}, '', '/static/spa/');

    const { createAppRouter } = await loadRouterModule();
    const router = createAppRouter();

    expect(router.options.history.location).toBe('/');
    expect(router.options.history.createHref('/analysis')).toBe('/static/spa/analysis');
  });

  it('bootstraps authenticated cold starts on /login and redirects to /', async () => {
    session.loadCurrentUser.mockImplementation(async () => {
      sessionState.currentUser = makeUser();
    });
    const { createAppRouter } = await loadRouterModule();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/login');

    expect(session.loadCurrentUser).toHaveBeenCalledTimes(1);
    expect(router.currentRoute.value.fullPath).toBe('/');
  });

  it('bootstraps forced-change cold starts on /login and redirects to /change-password', async () => {
    session.loadCurrentUser.mockImplementation(async () => {
      sessionState.currentUser = makeUser({ must_change_password: true });
    });
    const { createAppRouter } = await loadRouterModule();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/login');

    expect(session.loadCurrentUser).toHaveBeenCalledTimes(1);
    expect(router.currentRoute.value.fullPath).toBe('/change-password');
  });

  it('waits for an in-flight auth bootstrap before deciding protected navigation', async () => {
    const deferred = { resolve: null as null | (() => void) };
    session.loadCurrentUser.mockImplementation(() => {
      sessionState.loading = true;
      return new Promise<void>((resolve) => {
        deferred.resolve = () => {
          sessionState.currentUser = makeUser();
          sessionState.loading = false;
          resolve();
        };
      });
    });

    const { createAppRouter, ensureSessionLoaded } = await loadRouterModule();
    const router = createAppRouter(createMemoryHistory());

    const bootstrapPromise = ensureSessionLoaded();
    const navigationPromise = router.push('/analysis');

    expect(session.loadCurrentUser).toHaveBeenCalledTimes(1);

    if (!deferred.resolve) {
      throw new Error('Expected bootstrap resolver to be assigned.');
    }
    deferred.resolve();
    await bootstrapPromise;
    await navigationPromise;

    expect(router.currentRoute.value.fullPath).toBe('/analysis');
  });

  it('redirects users who must change password to /change-password', async () => {
    sessionState.currentUser = makeUser({ must_change_password: true });
    const { createAppRouter } = await loadRouterModule();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/runs');

    expect(router.currentRoute.value.fullPath).toBe('/change-password');
  });

  it('redirects authenticated users without a password change requirement away from /change-password', async () => {
    sessionState.currentUser = makeUser({ must_change_password: false });
    const { createAppRouter } = await loadRouterModule();
    const router = createAppRouter(createMemoryHistory());

    await router.push('/change-password');

    expect(router.currentRoute.value.fullPath).toBe('/');
  });

  it.each(['/settings', '/tenants', '/users'])('blocks non-admin users from navigating to %s', async (path) => {
    sessionState.currentUser = makeUser({ role: 'analyst' });
    const { createAppRouter } = await loadRouterModule();
    const router = createAppRouter(createMemoryHistory());

    await router.push(path);

    expect(router.currentRoute.value.fullPath).toBe('/');
  });

  it.each(['/settings', '/tenants', '/users'])('allows admin users to navigate to %s', async (path) => {
    sessionState.currentUser = makeUser({ role: 'admin' });
    const { createAppRouter } = await loadRouterModule();
    const router = createAppRouter(createMemoryHistory());

    await router.push(path);

    expect(router.currentRoute.value.fullPath).toBe(path);
  });
});
