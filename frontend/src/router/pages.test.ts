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
    ]);
    expect(navigationGroups.map((item) => item.labelKey)).toEqual([
      'nav.dashboard',
      'nav.analysis',
      'nav.runs',
      'nav.portfolio',
      'nav.workspace',
      'nav.automations',
      'nav.settings',
    ]);
    expect(navigationGroups.every((item) => item.descriptionKey.endsWith('Desc'))).toBe(true);
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
    ]);
  });
});
