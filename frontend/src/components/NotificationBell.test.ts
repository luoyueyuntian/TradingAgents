import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createMemoryHistory, createRouter } from 'vue-router';
const { apiGet } = vi.hoisted(() => ({ apiGet: vi.fn() }));
vi.mock('../services/api', () => ({ apiGet }));
vi.mock('../stores/session', () => ({ useSession: () => ({ apiContext: { value: { tenantId: 'a' } } }) }));
import NotificationBell from './NotificationBell.vue';
import { clearUnread } from '../stores/notifications';
async function page() {
  const router = createRouter({ history: createMemoryHistory(), routes: ['/', '/notifications'].map(path => ({ path, component: { template: '<div />' } })) });
  await router.push('/');
  const wrapper = mount(NotificationBell, { global: { plugins: [router] } });
  await flushPromises(); return { wrapper, router };
}
describe('notification bell', () => {
  beforeEach(() => { clearUnread(); apiGet.mockReset(); vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible'); });
  afterEach(() => { vi.useRealTimers(); vi.restoreAllMocks(); });
  it('shows 99+ with the real count in its accessible label and opens the center', async () => {
    apiGet.mockResolvedValue({ unread_count: 105 });
    const { wrapper, router } = await page();
    expect(wrapper.get('[data-testid="notification-badge"]').text()).toBe('99+');
    expect(wrapper.get('a').attributes('aria-label')).toContain('105');
    await wrapper.get('a').trigger('click'); await flushPromises();
    expect(router.currentRoute.value.path).toBe('/notifications'); wrapper.unmount();
  });
  it('hides the badge at zero', async () => {
    apiGet.mockResolvedValue({ unread_count: 0 });
    const { wrapper } = await page(); expect(wrapper.find('[data-testid="notification-badge"]').exists()).toBe(false); wrapper.unmount();
  });
  it('stops periodic refresh after unmount', async () => {
    vi.useFakeTimers(); apiGet.mockResolvedValue({ unread_count: 1 });
    const { wrapper } = await page();
    await vi.advanceTimersByTimeAsync(30000); const count = apiGet.mock.calls.length;
    wrapper.unmount(); await vi.advanceTimersByTimeAsync(60000);
    expect(apiGet.mock.calls).toHaveLength(count);
  });
});
