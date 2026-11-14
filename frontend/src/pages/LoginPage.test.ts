import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import LoginPage from './LoginPage.vue';

const loginMock = vi.hoisted(() => vi.fn());
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
    pushMock.mockReset();
    session.state.error = '';
    session.state.loading = false;
    session.mustChangePassword.value = false;
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
