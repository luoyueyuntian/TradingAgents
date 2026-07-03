import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';

import AppLayout from './AppLayout.vue';
import layoutSource from './AppLayout.vue?raw';
import { navigationGroups } from '../router/pages';
import { setLocale, useI18n } from '../i18n';
import { useSession } from '../stores/session';

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: navigationGroups.map((item) => ({
      path: item.path,
      component: { template: '<div />' },
    })),
  });
}

describe('AppLayout', () => {
  beforeEach(() => {
    const session = useSession();
    session.state.currentUser = {
      id: 'user-1',
      username: 'alice',
      email: 'alice@example.com',
      display_name: 'Alice Analyst',
      role: 'analyst',
      tenant_id: 'tenant-a',
      expires_at: null,
      must_change_password: false,
    };
  });

  it('lets page content use the full available width instead of capping at 1440px', async () => {
    const router = createTestRouter();
    await router.push('/');
    await router.isReady();

    const wrapper = mount(AppLayout, {
      global: {
        plugins: [router],
        stubs: {
          Button: true,
          Select: true,
          Tag: true,
        },
      },
    });

    const mainClasses = wrapper.get('main').attributes('class');

    expect(mainClasses).toContain('uno-w-full');
    expect(mainClasses).not.toContain('1440px');
  });

  it('keeps language and user menus in the right-side header actions', () => {
    expect(layoutSource).toContain('data-testid="header-actions"');
    expect(layoutSource).toContain('data-testid="language-menu"');
    expect(layoutSource).toContain('data-testid="user-menu"');
    expect(layoutSource).toContain('@click="changeLocale(option.value)"');
    expect(layoutSource).toContain('@mouseenter="userMenuOpen = true"');
    expect(layoutSource).toContain("{{ t(roleLabelKey) }}");
  });

  it('switches the app locale directly from the language menu', async () => {
    setLocale('en');
    const router = createTestRouter();
    await router.push('/');
    await router.isReady();

    const wrapper = mount(AppLayout, {
      global: {
        plugins: [router],
        stubs: {
          Button: true,
          Tag: true,
        },
      },
    });

    await wrapper.get('[data-testid="language-trigger"]').trigger('click');
    await wrapper.get('[data-testid="language-option-zh-CN"]').trigger('click');

    expect(useI18n().locale.value).toBe('zh-CN');
    expect(window.localStorage.getItem('tradingagents.locale')).toBe('zh-CN');
  });
});
