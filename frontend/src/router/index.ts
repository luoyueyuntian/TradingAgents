import { createRouter, createWebHistory, type RouterHistory } from 'vue-router';

import { routes } from './pages';
import { useSession } from '../stores/session';

let sessionBootstrapPromise: Promise<unknown> | null = null;

export async function ensureSessionLoaded() {
  const session = useSession();
  if (session.state.currentUser) {
    return;
  }
  if (!sessionBootstrapPromise) {
    sessionBootstrapPromise = session.loadCurrentUser()
      .catch(() => undefined)
      .finally(() => {
        sessionBootstrapPromise = null;
      });
  }
  await sessionBootstrapPromise;
}

export function createAppRouter(history: RouterHistory = createWebHistory()) {
  const router = createRouter({
    history,
    routes,
  });

  router.beforeEach(async (to) => {
    const session = useSession();
    const isLoginRoute = to.path === '/login';
    const isChangePasswordRoute = to.path === '/change-password';
    const shouldBootstrapSession = !session.state.currentUser && (Boolean(to.meta.requiresAuth) || isLoginRoute);

    if (shouldBootstrapSession) {
      await ensureSessionLoaded();
    }

    const isAuthenticated = Boolean(session.state.currentUser);
    const mustChangePassword = session.mustChangePassword.value;

    if (!isAuthenticated) {
      if (to.meta.requiresAuth && !isLoginRoute) {
        return { path: '/login' };
      }
      return true;
    }

    if (isLoginRoute) {
      return mustChangePassword ? { path: '/change-password' } : { path: '/' };
    }

    if (isChangePasswordRoute && !mustChangePassword) {
      return { path: '/' };
    }

    if (mustChangePassword && !isChangePasswordRoute) {
      return { path: '/change-password' };
    }

    if (to.meta.minRole === 'admin' && !session.isAdmin.value) {
      return { path: '/' };
    }

    return true;
  });

  return router;
}

export const router = createAppRouter();
