import type { RouteRecordRaw } from 'vue-router';

import type { MessageKey } from '../i18n';

export type RouteMinRole = 'admin';

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean;
    minRole?: RouteMinRole;
  }
}

export type NavigationSection = 'research' | 'workspace' | 'administration';

export const navigationSections: { id: NavigationSection; labelKey: MessageKey }[] = [
  { id: 'research', labelKey: 'nav.sectionResearch' },
  { id: 'workspace', labelKey: 'nav.sectionWorkspace' },
  { id: 'administration', labelKey: 'nav.sectionAdministration' },
];

export type NavigationGroup = {
  section: NavigationSection;
  labelKey: MessageKey;
  icon: string;
  path: string;
  descriptionKey: MessageKey;
  minRole?: RouteMinRole;
};

const pageModules = import.meta.glob('../pages/*.vue');

function loadPage(path: string) {
  return () => {
    const loader = pageModules[path];
    if (!loader) {
      return Promise.reject(new Error(`Missing page component for route: ${path}`));
    }
    return loader();
  };
}

export const navigationGroups: NavigationGroup[] = [
  {
    section: 'research',
    labelKey: 'nav.dashboard',
    icon: 'pi pi-home',
    path: '/',
    descriptionKey: 'nav.dashboardDesc',
  },
  {
    section: 'research',
    labelKey: 'nav.analysis',
    icon: 'pi pi-play-circle',
    path: '/analysis',
    descriptionKey: 'nav.analysisDesc',
  },
  {
    section: 'research',
    labelKey: 'nav.runs',
    icon: 'pi pi-list-check',
    path: '/runs',
    descriptionKey: 'nav.runsDesc',
  },
  {
    section: 'workspace',
    labelKey: 'nav.portfolio',
    icon: 'pi pi-chart-line',
    path: '/portfolio',
    descriptionKey: 'nav.portfolioDesc',
  },
  {
    section: 'workspace',
    labelKey: 'nav.workspace',
    icon: 'pi pi-objects-column',
    path: '/workspace',
    descriptionKey: 'nav.workspaceDesc',
  },
  {
    section: 'workspace',
    labelKey: 'nav.automations',
    icon: 'pi pi-clock',
    path: '/automations',
    descriptionKey: 'nav.automationsDesc',
  },
  {
    section: 'administration',
    labelKey: 'nav.settings',
    icon: 'pi pi-cog',
    path: '/settings',
    descriptionKey: 'nav.settingsDesc',
    minRole: 'admin',
  },
  {
    section: 'administration',
    labelKey: 'nav.tenants',
    icon: 'pi pi-building',
    path: '/tenants',
    descriptionKey: 'nav.tenantsDesc',
    minRole: 'admin',
  },
  {
    section: 'administration',
    labelKey: 'nav.users',
    icon: 'pi pi-users',
    path: '/users',
    descriptionKey: 'nav.usersDesc',
    minRole: 'admin',
  },
];

const requiresAuth = { requiresAuth: true } as const;

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('../pages/DashboardPage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/analysis',
    name: 'analysis',
    component: () => import('../pages/AnalyzePage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/runs',
    name: 'runs',
    component: () => import('../pages/RunsPage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/runs/:runId',
    name: 'run-detail',
    component: () => import('../pages/RunDetailPage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/portfolio',
    name: 'portfolio',
    component: () => import('../pages/PortfolioPage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/portfolio/watchlist',
    name: 'portfolio-watchlist',
    component: () => import('../pages/PortfolioWatchlistPage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/portfolio/positions',
    name: 'portfolio-positions',
    component: () => import('../pages/PortfolioPositionsPage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/portfolio/stock-groups',
    name: 'portfolio-stock-groups',
    component: () => import('../pages/PortfolioStockGroupsPage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/portfolio/alerts',
    name: 'portfolio-alerts',
    component: () => import('../pages/PortfolioAlertsPage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/workspace',
    name: 'workspace',
    component: () => import('../pages/WorkspacePage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/automations',
    name: 'automations',
    component: () => import('../pages/AutomationsPage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../pages/SettingsPage.vue'),
    meta: {
      requiresAuth: true,
      minRole: 'admin',
    },
  },
  {
    path: '/tenants',
    name: 'tenants',
    component: loadPage('../pages/TenantsPage.vue'),
    meta: {
      requiresAuth: true,
      minRole: 'admin',
    },
  },
  {
    path: '/tenants/:tenantId',
    name: 'tenant-detail',
    component: loadPage('../pages/TenantDetailPage.vue'),
    meta: {
      requiresAuth: true,
      minRole: 'admin',
    },
  },
  {
    path: '/users',
    name: 'users',
    component: () => import('../pages/UserManagementPage.vue'),
    meta: {
      requiresAuth: true,
      minRole: 'admin',
    },
  },
  {
    path: '/profile',
    name: 'profile',
    component: () => import('../pages/ProfilePage.vue'),
    meta: requiresAuth,
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('../pages/LoginPage.vue'),
  },
  {
    path: '/change-password',
    name: 'change-password',
    component: () => import('../pages/ForcePasswordChangePage.vue'),
    meta: requiresAuth,
  },
];
