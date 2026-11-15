import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import LoginPage from './LoginPage.vue';

const loginMock = vi.hoisted(() => vi.fn());
const guestGetMock = vi.hoisted(() => vi.fn());
vi.mock('../services/api', () => ({ apiGet: guestGetMock }));
const pushMock = vi.hoisted(() => vi.fn());

const session = {
  state: {
    error: '',
    loading: false,
  },
  mustChangePassword: { value: false },
  login: loginMock,
};

vi.mock('../stores/session', () => ({
  useSession: () => session,
}));

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

const ButtonStub = {
  props: ['label', 'type', 'loading'],
  template: `<button :type="type || 'button'">{{ label }}</button>`,
};

const CardStub = {
  template: '<div><slot name="title" /><slot name="content" /></div>',
};

const InputTextStub = {
  props: ['modelValue', 'id', 'type', 'autocomplete', 'placeholder'],
  emits: ['update:modelValue'],
  template: `
    <input
      :id="id"
      :type="type || 'text'"
      :value="modelValue"
      :autocomplete="autocomplete"
      :placeholder="placeholder"
      @input="$emit('update:modelValue', $event.target.value)"
    >
  `,
};

const MessageStub = {
  template: '<div><slot /></div>',
};

function mountPage() {
  return mount(LoginPage, {
    global: {
      stubs: {
        Button: ButtonStub,
        Card: CardStub,
        InputText: InputTextStub,
        Message: MessageStub,
      },
    },
  });
}

describe('LoginPage', () => {
  beforeEach(() => {
    loginMock.mockReset();
    guestGetMock.mockReset(); guestGetMock.mockResolvedValue(null);
    pushMock.mockReset();
    session.state.error = '';
    session.state.loading = false;
    session.mustChangePassword.value = false;
  });

  it('switches in place to a guest form with locked credentials and does not sign in until submitted', async () => {
    guestGetMock.mockResolvedValue({ username: 'guest', password: 'PublicDemo42!', tenant_id: 'default' });
    const wrapper = mountPage(); await flushPromises();
    expect(wrapper.find('[data-testid="guest-access"]').exists()).toBe(false);
    await wrapper.get('[data-testid="guest-login-entry"]').trigger('click'); await flushPromises();
    expect(loginMock).not.toHaveBeenCalled(); expect(pushMock).not.toHaveBeenCalled();
    expect((wrapper.get('#login-identifier').element as HTMLInputElement).value).toBe('guest');
    expect((wrapper.get('#login-password').element as HTMLInputElement).value).toBe('PublicDemo42!');
    expect(wrapper.get('#login-identifier').attributes('readonly')).toBeDefined();
    expect(wrapper.get('#login-password').attributes('readonly')).toBeDefined();
    expect(wrapper.text()).toMatch(/访客可查看现有仪表盘|Guests can view/);
    await wrapper.get('#login-identifier').setValue('tampered');
    await wrapper.get('form').trigger('submit.prevent'); await flushPromises();
    expect(loginMock).toHaveBeenCalledWith('guest','PublicDemo42!');
  });
  it('returns to the normal form and preserves its input without navigation', async () => {
    guestGetMock.mockResolvedValue({ username: 'guest', password: 'PublicDemo42!', tenant_id: 'default' });
    const wrapper = mountPage(); await flushPromises();
    await wrapper.get('#login-identifier').setValue('alice');
    await wrapper.get('#login-password').setValue('PrivatePass42!');
    await wrapper.get('[data-testid="guest-login-entry"]').trigger('click');
    await wrapper.get('[data-testid="guest-login-back"]').trigger('click');
    expect((wrapper.get('#login-identifier').element as HTMLInputElement).value).toBe('alice');
    expect((wrapper.get('#login-password').element as HTMLInputElement).value).toBe('PrivatePass42!');
    expect(wrapper.get('#login-identifier').attributes('readonly')).toBeUndefined();
    expect(pushMock).not.toHaveBeenCalled(); expect(loginMock).not.toHaveBeenCalled();
  });
  it('does not show an unavailable guest account', async () => {
    const wrapper = mountPage(); await flushPromises();
    expect(wrapper.find('[data-testid="guest-login-entry"]').exists()).toBe(false);
  });
  it('logs in with account credentials without a tenant field', async () => {
    loginMock.mockResolvedValue(undefined);
    const wrapper = mountPage();

    expect(wrapper.find('#login-tenant').exists()).toBe(false);
    await wrapper.get('#login-identifier').setValue('alice');
    await wrapper.get('#login-password').setValue('StrongPass123!');
    await wrapper.get('form').trigger('submit.prevent');
    await flushPromises();

    expect(loginMock).toHaveBeenCalledWith('alice', 'StrongPass123!');
    expect(pushMock).toHaveBeenCalledWith('/');
  });
});
