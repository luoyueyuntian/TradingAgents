import { createRouter, createWebHistory, type RouterHistory } from 'vue-router';

import { routes } from './pages';
import { useSession } from '../stores/session';

let sessionBootstrapPromise: Promise<unknown> | null = null;

async function ensureSessionLoaded() {
  const session = useSession();
  if (session.state.currentUser || session.state.loading) {
    return;
  }
  if (!sessionBootstrapPromise) {
    sessionBootstrapPromise = session.loadCurrentUser().catch(() => undefined);
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
    const isPublicRoute = isLoginRoute;

    if (!isPublicRoute && !session.state.currentUser) {
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
