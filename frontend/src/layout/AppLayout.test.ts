import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';

import AppLayout from './AppLayout.vue';
import layoutSource from './AppLayout.vue?raw';
import { navigationGroups } from '../router/pages';
import { setLocale, useI18n } from '../i18n';
import * as apiService from '../services/api';
import { useSession } from '../stores/session';

function createTestRouter() {
  return createRouter({
    history: createMemoryHistory(),
    routes: [...navigationGroups, { path: '/runs/:runId' }, { path: '/portfolio/positions' }, { path: '/tenants/:tenantId' }, { path: '/profile' }].map((item) => ({
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
    session.state.currentMemberId = 'member-2';
    vi.spyOn(apiService, 'apiGet').mockImplementation(async (path: string) => {
      if (path === '/api/members') {
        return [
          { id: 'member-1', name: 'Alice Analyst' },
          { id: 'member-2', name: 'Bob Builder' },
        ];
      }
      if (path === '/api/settings') {
        return {
          workspace: {
            default_ui_language: 'zh-CN',
          },
        };
      }
      throw new Error(`Unexpected apiGet path: ${path}`);
    });
  });

  it('groups navigation by purpose and omits the entire management section for analysts', async () => {
    setLocale('zh-CN');
    const router = createTestRouter();
    await router.push('/');
    const wrapper = mount(AppLayout, { global: { plugins: [router], stubs: { Button: true } } });
    const nav = wrapper.get('aside nav');
    expect(nav.findAll('h2').map((heading) => heading.text())).toEqual(['分析与研究', '投资与协作']);
    expect(nav.text()).toContain('发起分析');
    expect(nav.text()).toContain('投资组合');
    expect(nav.find('a[href="/settings"]').exists()).toBe(false);
    useSession().state.currentUser!.role = 'admin';
    await flushPromises();
    expect(nav.findAll('h2').map((heading) => heading.text())).toEqual(['分析与研究', '投资与协作', '系统管理']);
    expect(nav.find('a[href="/settings"]').exists()).toBe(true);
    wrapper.unmount();
  });

  it.each([
    ['/runs/run-123', '/runs'],
    ['/portfolio/positions', '/portfolio'],
    ['/tenants/tenant-a', '/tenants'],
    ['/', '/'],
  ])('keeps exactly the owning navigation item highlighted at %s', async (path, owner) => {
    useSession().state.currentUser!.role = 'admin';
    const router = createTestRouter();
    await router.push(path);
    const wrapper = mount(AppLayout, { global: { plugins: [router], stubs: { Button: true } } });
    const active = wrapper.findAll('aside nav a[aria-current="page"]');
    expect(active).toHaveLength(1);
    expect(active[0].attributes('href')).toBe(owner);
    await router.push('/analysis');
    expect(wrapper.get('aside nav a[aria-current="page"]').attributes('href')).toBe('/analysis');
    wrapper.unmount();
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
          Select: true,
          Tag: true,
        },
      },
    });

    await wrapper.get('[data-testid="language-trigger"]').trigger('click');
    await wrapper.get('[data-testid="language-option-zh-CN"]').trigger('click');

    expect(useI18n().locale.value).toBe('zh-CN');
    expect(window.localStorage.getItem('tradingagents.locale')).toBe('zh-CN');
  });

  it('renders the language trigger as plain text and flips the chevron when open', async () => {
    setLocale('en');
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

    const trigger = wrapper.get('[data-testid="language-trigger"]');

    expect(trigger.text()).toContain('English');
    expect(trigger.classes()).toContain('uno-bg-transparent');
    expect(trigger.classes()).not.toContain('uno-border');
    expect(trigger.find('.pi-angle-down').exists()).toBe(true);

    await trigger.trigger('click');

    expect(wrapper.get('[data-testid="language-trigger"]').find('.pi-angle-up').exists()).toBe(true);
  });

  it('hides the language menu when clicking outside the menu', async () => {
    setLocale('en');
    const router = createTestRouter();
    await router.push('/');
    await router.isReady();

    const wrapper = mount(AppLayout, {
      attachTo: document.body,
      global: {
        plugins: [router],
        stubs: {
          Button: true,
          Select: true,
          Tag: true,
        },
      },
    });

    await wrapper.get('[data-testid="language-trigger"]').trigger('click');
    expect(wrapper.find('[data-testid="language-option-zh-CN"]').exists()).toBe(true);

    document.body.click();
    await flushPromises();

    expect(wrapper.find('[data-testid="language-option-zh-CN"]').exists()).toBe(false);
    wrapper.unmount();
  });

  it('applies the saved default UI language when no explicit locale override exists', async () => {
    window.localStorage.clear();
    vi.mocked(apiService.apiGet).mockImplementation(async (path: string) => {
      if (path === '/api/members') {
        return [
          { id: 'member-1', name: 'Alice Analyst' },
          { id: 'member-2', name: 'Bob Builder' },
        ];
      }
      if (path === '/api/settings') {
        return {
          workspace: {
            default_ui_language: 'en',
          },
        };
      }
      throw new Error(`Unexpected apiGet path: ${path}`);
    });

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

    await flushPromises();

    expect(useI18n().locale.value).toBe('en');
    expect(window.localStorage.getItem('tradingagents.defaultLocale')).toBe('en');
    wrapper.unmount();
  });

  it('renders the user menu trigger as plain text and flips the chevron when open', async () => {
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

    const trigger = wrapper.get('[data-testid="user-menu-trigger"]');

    expect(trigger.text()).toContain('Alice Analyst');
    expect(trigger.classes()).toContain('uno-bg-transparent');
    expect(trigger.classes()).not.toContain('uno-border');
    expect(trigger.find('.pi-angle-down').exists()).toBe(true);

    await wrapper.get('[data-testid="user-menu"]').trigger('mouseenter');

    expect(wrapper.get('[data-testid="user-menu-trigger"]').find('.pi-angle-up').exists()).toBe(true);
  });

  it('shows the logged-in user without a separate member selector', async () => {
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

    await flushPromises();

    expect(wrapper.find('[data-testid="current-member-menu"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="current-member-trigger"]').exists()).toBe(false);
    expect(wrapper.get('[data-testid="user-menu-trigger"]').text()).toContain('Alice Analyst');
    expect(wrapper.text()).not.toContain('Bob Builder');
    wrapper.unmount();
  });
});
