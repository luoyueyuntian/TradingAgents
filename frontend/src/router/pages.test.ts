import { beforeAll, describe, expect, it, vi } from 'vitest';

vi.mock('../pages/TenantsPage.vue', () => ({ default: { name: 'TenantsPage' } }), { virtual: true });
vi.mock('../pages/TenantDetailPage.vue', () => ({ default: { name: 'TenantDetailPage' } }), { virtual: true });

let navigationGroups: typeof import('./pages').navigationGroups;
let routes: typeof import('./pages').routes;

beforeAll(async () => {
  ({ navigationGroups, routes } = await import('./pages'));
});

describe('page registry', () => {
  it('splits the workspace into the requested primary SPA pages', () => {
    expect(navigationGroups.map((item) => item.path)).toEqual([
      '/',
      '/analysis',
      '/runs',
      '/portfolio',
      '/workspace',
      '/automations',
      '/settings',
      '/tenants',
      '/users',
    ]);
    expect(navigationGroups.map((item) => item.labelKey)).toEqual([
      'nav.dashboard',
      'nav.analysis',
      'nav.runs',
      'nav.portfolio',
      'nav.workspace',
      'nav.automations',
      'nav.settings',
      'nav.tenants',
      'nav.users',
    ]);
    expect(navigationGroups.every((item) => item.descriptionKey.endsWith('Desc'))).toBe(true);
    expect(navigationGroups.find((item) => item.path === '/settings')?.minRole).toBe('admin');
    expect(navigationGroups.find((item) => item.path === '/tenants')?.minRole).toBe('admin');
    expect(navigationGroups.find((item) => item.path === '/users')?.minRole).toBe('admin');
  });

  it('uses unique route paths and stable route names', () => {
    const paths = routes.map((route) => route.path);
    const names = routes.map((route) => String(route.name));

    expect(new Set(paths).size).toBe(paths.length);
    expect(new Set(names).size).toBe(names.length);
    expect(names).toEqual([
      'dashboard',
      'analysis',
      'runs',
      'run-detail',
      'portfolio',
      'workspace',
      'automations',
      'settings',
      'tenants',
      'tenant-detail',
      'users',
      'login',
      'change-password',
    ]);
    expect(routes.find((route) => route.path === '/runs/:runId')?.name).toBe('run-detail');
    expect(routes.find((route) => route.path === '/settings')?.meta?.minRole).toBe('admin');
    expect(routes.find((route) => route.path === '/tenants')?.meta?.minRole).toBe('admin');
    expect(routes.find((route) => route.path === '/tenants/:tenantId')?.meta?.minRole).toBe('admin');
    expect(routes.find((route) => route.path === '/users')?.meta?.minRole).toBe('admin');
    expect(routes.filter((route) => route.meta?.requiresAuth).length).toBe(12);
  });
});
