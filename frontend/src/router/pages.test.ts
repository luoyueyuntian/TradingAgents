import { describe, expect, it } from 'vitest';

import { navigationGroups, routes } from './pages';

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
      'nav.users',
    ]);
    expect(navigationGroups.every((item) => item.descriptionKey.endsWith('Desc'))).toBe(true);
    expect(navigationGroups.find((item) => item.path === '/settings')?.minRole).toBe('admin');
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
      'portfolio',
      'workspace',
      'automations',
      'settings',
      'users',
      'login',
      'change-password',
    ]);
    expect(routes.find((route) => route.path === '/settings')?.meta?.minRole).toBe('admin');
    expect(routes.find((route) => route.path === '/users')?.meta?.minRole).toBe('admin');
    expect(routes.filter((route) => route.meta?.requiresAuth).length).toBe(9);
  });
});
