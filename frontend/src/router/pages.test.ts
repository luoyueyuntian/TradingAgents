import { describe, expect, it } from 'vitest';
import pageSource from './pages.ts?raw';

describe('page registry', () => {
  it('splits the workspace into the requested primary SPA pages', () => {
    expect(pageSource).toContain("path: '/tenants'");
    expect(pageSource).toContain("labelKey: 'nav.tenants'");
    expect(pageSource).toContain("descriptionKey: 'nav.tenantsDesc'");
    expect(pageSource).toContain("path: '/settings'");
    expect(pageSource).toContain("path: '/users'");
  });

  it('uses unique route paths and stable route names', () => {
    expect(pageSource).toContain("name: 'tenants'");
    expect(pageSource).toContain("path: '/tenants/:tenantId'");
    expect(pageSource).toContain("name: 'tenant-detail'");
    expect(pageSource).toContain("component: () => import('../pages/TenantsPage.vue')");
    expect(pageSource).toContain("component: () => import('../pages/TenantDetailPage.vue')");
    expect(pageSource).not.toContain('const pageModules = import.meta.glob');
    expect(pageSource).not.toContain('function loadPage(');
    expect(pageSource).not.toContain('fallbackPath');
  });
});
