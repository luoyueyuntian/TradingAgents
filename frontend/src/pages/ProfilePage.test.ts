import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import ProfilePage from './ProfilePage.vue';

const { apiGet, apiPut, apiPost, refreshUser } = vi.hoisted(() => ({ apiGet: vi.fn(), apiPut: vi.fn(), apiPost: vi.fn(), refreshUser: vi.fn() }));
vi.mock('../services/api', () => ({ apiGet, apiPut, apiPost }));
vi.mock('../stores/session', () => ({ useSession: () => ({ loadCurrentUser: refreshUser }) }));
const data = { user: { username: 'alice', display_name: 'Alice', email: 'alice@example.com', role: 'viewer', tenant_id: 'tenant-a' }, email_verification_available: false, sessions: [{ current: true, created_at: 1, last_seen_at: 1, expires_at: 2 }] };
function page() {
  return mount(ProfilePage, { global: { stubs: {
    PageHeader: { template: '<div />' },
    ForcePasswordChangePage: { props: ['embedded'], template: '<div data-testid="embedded-password" />' },
    Card: { template: '<div><slot name="title"/><slot name="content"/></div>' },
    Message: { template: '<div><slot/></div>' },
    InputText: { props: ['modelValue', 'disabled'], emits: ['update:modelValue'], template: '<input :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', $event.target.value)" />' },
    Button: { props: ['label', 'type', 'disabled'], template: '<button :type="type || \'button\'" :disabled="disabled">{{label}}</button>' },
    Select: true,
  } } });
}
describe('ProfilePage', () => {
  beforeEach(() => { vi.clearAllMocks(); apiGet.mockResolvedValue(data); apiPut.mockResolvedValue({}); refreshUser.mockResolvedValue({}); });
  it('shows account details and the embedded password form, with mail disabled honestly', async () => {
    const wrapper = page(); await flushPromises();
    expect(wrapper.text()).toContain('alice@example.com');
    expect(wrapper.text()).toContain('tenant-a');
    expect(wrapper.find('[data-testid="embedded-password"]').exists()).toBe(true);
    expect(wrapper.get('#profile-email').attributes('disabled')).toBeDefined();
    expect(wrapper.text()).toMatch(/尚未配置邮件|not configured/);
  });
  it('saves only nickname via a session-only API and refreshes the user menu', async () => {
    const wrapper = page(); await flushPromises();
    await wrapper.get('#profile-nickname').setValue('Updated');
    await wrapper.findAll('form')[0]!.trigger('submit'); await flushPromises();
    expect(apiPut).toHaveBeenCalledWith('/api/auth/profile', { display_name: 'Updated' }, {});
    expect(refreshUser).toHaveBeenCalled();
  });
  it('clears pending email confirmation when the target address changes', async () => {
    apiGet.mockResolvedValue({ ...data, email_verification_available: true });
    apiPost.mockResolvedValue({ sent: true });
    const wrapper = page(); await flushPromises();
    await wrapper.get('#profile-email').setValue('first@example.com');
    const send = wrapper.findAll('button').find((item) => /发送验证码|Send verification code/.test(item.text()));
    await send!.trigger('click'); await flushPromises();
    expect(wrapper.get('#profile-code').attributes('disabled')).toBeUndefined();
    await wrapper.get('#profile-email').setValue('second@example.com');
    expect(wrapper.get('#profile-code').attributes('disabled')).toBeDefined();
    expect(wrapper.text()).toMatch(/新邮箱已变化|target address changed/);
    wrapper.unmount();
  });
  it('does not claim a nickname save succeeded if the server rejects it', async () => {
    apiPut.mockRejectedValue(new Error('Save failed'));
    const wrapper = page(); await flushPromises();
    await wrapper.findAll('form')[0]!.trigger('submit'); await flushPromises();
    expect(wrapper.text()).toContain('Save failed');
  });
});
