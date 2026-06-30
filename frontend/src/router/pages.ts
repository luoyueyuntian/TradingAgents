import type { RouteRecordRaw } from 'vue-router';

import type { MessageKey } from '../i18n';

export type NavigationGroup = {
  labelKey: MessageKey;
  icon: string;
  path: string;
  descriptionKey: MessageKey;
};

export const navigationGroups: NavigationGroup[] = [
  {
    labelKey: 'nav.dashboard',
    icon: 'pi pi-home',
    path: '/',
    descriptionKey: 'nav.dashboardDesc',
  },
  {
    labelKey: 'nav.analysis',
    icon: 'pi pi-play-circle',
    path: '/analysis',
    descriptionKey: 'nav.analysisDesc',
  },
  {
    labelKey: 'nav.runs',
    icon: 'pi pi-list-check',
    path: '/runs',
    descriptionKey: 'nav.runsDesc',
  },
  {
    labelKey: 'nav.portfolio',
    icon: 'pi pi-chart-line',
    path: '/portfolio',
    descriptionKey: 'nav.portfolioDesc',
  },
  {
    labelKey: 'nav.workspace',
    icon: 'pi pi-objects-column',
    path: '/workspace',
    descriptionKey: 'nav.workspaceDesc',
  },
  {
    labelKey: 'nav.automations',
    icon: 'pi pi-clock',
    path: '/automations',
    descriptionKey: 'nav.automationsDesc',
  },
  {
    labelKey: 'nav.settings',
    icon: 'pi pi-cog',
    path: '/settings',
    descriptionKey: 'nav.settingsDesc',
  },
];

export const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'dashboard',
    component: () => import('../pages/DashboardPage.vue'),
  },
  {
    path: '/analysis',
    name: 'analysis',
    component: () => import('../pages/AnalyzePage.vue'),
  },
  {
    path: '/runs',
    name: 'runs',
    component: () => import('../pages/RunsPage.vue'),
  },
  {
    path: '/portfolio',
    name: 'portfolio',
    component: () => import('../pages/PortfolioPage.vue'),
  },
  {
    path: '/workspace',
    name: 'workspace',
    component: () => import('../pages/WorkspacePage.vue'),
  },
  {
    path: '/automations',
    name: 'automations',
    component: () => import('../pages/AutomationsPage.vue'),
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('../pages/SettingsPage.vue'),
  },
];
