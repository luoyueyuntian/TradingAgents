import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import ForcePasswordChangePage from './ForcePasswordChangePage.vue';

const changePasswordMock = vi.hoisted(() => vi.fn());
const pushMock = vi.hoisted(() => vi.fn());

const session = {
  state: {
    error: '',
    loading: false,
  },
  mustChangePassword: { value: false },
  changePassword: changePasswordMock,
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

function mountPage(props: { embedded?: boolean } = {}) {
  return mount(ForcePasswordChangePage, {
    props,
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

describe('ForcePasswordChangePage', () => {
  beforeEach(() => {
    changePasswordMock.mockReset();
    pushMock.mockReset();
    session.state.error = '';
    session.state.loading = false;
  });
  it('explains session-based changes and every password rule', () => {
    const wrapper = mountPage();
    expect(wrapper.get('[data-testid="password-change-tips"]').text()).toMatch(/无需输入当前密码|current password is not required/);
    expect(wrapper.text()).toContain('10');
    expect(wrapper.text()).toMatch(/用户名|username/);
    expect(wrapper.text()).toMatch(/邮箱|email/);
  });
  it('explains a expired session and how to retry without showing raw errors', async () => {
    changePasswordMock.mockRejectedValue(new Error('Unauthorized'));
    const wrapper = mountPage();
    await wrapper.get('#confirm-password').setValue('StrongPassword42!');
    await wrapper.get('#new-password').setValue('StrongPassword42!');
    await wrapper.get('form').trigger('submit');
    await flushPromises();
    expect(wrapper.text()).not.toContain('Invalid credentials');
    expect(wrapper.text()).toMatch(/登录状态已失效|session has expired/);
    expect(wrapper.find('#current-password').exists()).toBe(false);
    expect(pushMock).not.toHaveBeenCalled();
  });
  it('requires matching confirmation before submitting', async () => {
    const wrapper = mountPage();
    await wrapper.get('#new-password').setValue('NewStrongPassword42!');
    await wrapper.get('#confirm-password').setValue('different');
    await wrapper.get('form').trigger('submit');
    expect(changePasswordMock).not.toHaveBeenCalled();
    expect(wrapper.text()).toMatch(/不一致|do not match/);
  });
  it('stays in the personal center and confirms success when embedded', async () => {
    changePasswordMock.mockResolvedValue({});
    const wrapper = mountPage({ embedded: true });
    await wrapper.get('#new-password').setValue('NewStrongPassword42!');
    await wrapper.get('#confirm-password').setValue('NewStrongPassword42!');
    await wrapper.get('form').trigger('submit'); await flushPromises();
    expect(pushMock).not.toHaveBeenCalled();
    expect(wrapper.emitted('changed')).toHaveLength(1);
    expect(wrapper.text()).toMatch(/密码修改成功|Password changed/);
  });
  it('does not submit missing passwords' , async () => {
    const wrapper = mountPage();
    await wrapper.get('form').trigger('submit');
    expect(changePasswordMock).not.toHaveBeenCalled();
    expect(wrapper.text()).toMatch(/请填写新密码|Enter a new password/);
  });
  it('sends the supplied passwords and navigates only on success', async () => {
    changePasswordMock.mockResolvedValue({});
    const wrapper = mountPage();
    await wrapper.get('#confirm-password').setValue('NewStrongPassword42!');
    await wrapper.get('#new-password').setValue('NewStrongPassword42!');
    await wrapper.get('form').trigger('submit');
    await flushPromises();
    expect(changePasswordMock).toHaveBeenCalledWith('NewStrongPassword42!');
    expect(pushMock).toHaveBeenCalledWith('/');
  });
});
