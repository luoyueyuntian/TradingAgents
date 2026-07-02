import { mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';

import AppLayout from './AppLayout.vue';
import { navigationGroups } from '../router/pages';

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
  it('lets page content use the full available width instead of capping at 1440px', async () => {
    const router = createTestRouter();
    await router.push('/');
    await router.isReady();

    const wrapper = mount(AppLayout, {
      global: {
        plugins: [router],
        stubs: {
          Button: true,
          InputText: true,
          Select: true,
        },
      },
    });

    const mainClasses = wrapper.get('main').attributes('class');

    expect(mainClasses).toContain('uno-w-full');
    expect(mainClasses).not.toContain('1440px');
  });
});
