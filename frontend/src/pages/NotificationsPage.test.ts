import { enableAutoUnmount, flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
const { apiGet, apiPost, refreshUnread } = vi.hoisted(() => ({ apiGet: vi.fn(), apiPost: vi.fn(), refreshUnread: vi.fn() }));
vi.mock('../services/api', () => ({ apiGet, apiPost }));
vi.mock('../stores/notifications', () => ({ refreshUnread }));
import { reactive } from 'vue';
enableAutoUnmount(afterEach);
const session = reactive({ canWrite: { value: true }, apiContext: { value: { tenantId: 'a' } } });
vi.mock('../stores/session', () => ({ useSession: () => session }));
import NotificationsPage from './NotificationsPage.vue';
const item = { id: 'run:one:completed', run_id: 'one', kind: 'run', severity: 'info', title: 'Test analysis complete', message: 'Report ready', is_read: false, created_at: 1794700000000 };
function page() { return mount(NotificationsPage, { global: { stubs: {
  PageHeader: { template: '<div><slot name="actions" /></div>' },
  Card: { template: '<div><slot name="content" /></div>' },
  Button: { props: ['label', 'disabled'], template: '<button :disabled="disabled">{{ label }}</button>' },
  Select: { props: ['modelValue', 'options'], emits: ['update:modelValue'], template: '<select :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><option v-for="item in options" :value="item.value" :key="item.value">{{item.label}}</option></select>' },
  Tag: { props: ['value'], template: '<span>{{value}}</span>' }, Message: { template: '<div><slot /></div>' }, RouterLink: { props: ['to'], template: '<a :href="to"><slot /></a>' },
} } }); }
function button(wrapper: ReturnType<typeof page>, pattern: RegExp) { return wrapper.findAll('button').find(b => pattern.test(b.text()))!; }
describe('message center', () => {
  beforeEach(() => { vi.clearAllMocks(); session.apiContext.value.tenantId = 'a'; session.canWrite.value = true; apiGet.mockResolvedValue({ items: [item], unread_count: 1, filtered_count: 25 }); apiPost.mockResolvedValue({}); refreshUnread.mockResolvedValue(undefined); });
  it('renders complete messages and pages beyond the first page', async () => {
    const wrapper = page(); await flushPromises(); expect(wrapper.text()).toContain('Report ready');
    expect(wrapper.get('a').attributes('href')).toBe('/runs/one');
    await button(wrapper, /下一页|Next/).trigger('click'); await flushPromises();
    expect(apiGet.mock.lastCall?.[0]).toContain('offset=20');
  });
  it('marks an individual item read and refreshes the shared badge', async () => {
    const wrapper = page(); await flushPromises();
    await button(wrapper, /^标为已读$|^Mark as read$/).trigger('click'); await flushPromises();
    expect(apiPost).toHaveBeenCalledWith('/api/notifications/run%3Aone%3Acompleted/read', {}, session.apiContext.value);
    expect(refreshUnread).toHaveBeenCalled();
  });
  it('uses the supported warning filter value and resets paging', async () => {
    const wrapper = page(); await flushPromises();
    await wrapper.findAll('select')[1]!.setValue('warning'); await flushPromises();
    expect(apiGet.mock.lastCall?.[0]).toContain('severity=warning'); expect(apiGet.mock.lastCall?.[0]).toContain('offset=0');
  });
  it('shows failures without pretending the list is empty', async () => {
    apiGet.mockRejectedValue(new Error('Server unavailable')); const wrapper = page(); await flushPromises();
    expect(wrapper.text()).toContain('Server unavailable'); expect(wrapper.text()).not.toMatch(/暂无消息|No messages match/);
  });
  it.each(['b', 'a'])('ignores a stale read failure after switching tenants (ending in %s)', async (target) => {
    let reject!: (error: Error) => void;
    apiPost.mockReturnValueOnce(new Promise((_resolve, fail) => { reject = fail; }));
    const wrapper = page(); await flushPromises();
    await button(wrapper, /^标为已读$|^Mark as read$/).trigger('click');
    session.apiContext.value.tenantId = 'b'; await flushPromises();
    if (target === 'a') { session.apiContext.value.tenantId = 'a'; await flushPromises(); }
    reject(new Error('old-tenant-failure')); await flushPromises();
    expect(wrapper.text()).not.toContain('old-tenant-failure');
    expect(button(wrapper, /当前筛选全部已读|Mark all filtered/).attributes('disabled')).toBeUndefined();
  });
  it('does not offer mutation actions to read-only users', async () => {
    session.canWrite.value = false; const wrapper = page(); await flushPromises();
    expect(wrapper.findAll('button').some(b => /^标为已读$|^Mark as read$/.test(b.text()))).toBe(false);
    expect(button(wrapper, /当前筛选全部已读|Mark all filtered/).attributes('disabled')).toBeDefined();
  });
});
