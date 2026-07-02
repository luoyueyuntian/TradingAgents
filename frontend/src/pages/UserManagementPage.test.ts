import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import UserManagementPage from './UserManagementPage.vue';

const { apiGet, apiPost, apiPatch, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

vi.mock('../services/api', () => ({
  apiGet,
  apiPost,
  apiPatch,
  apiDelete,
}));

const session = {
  apiContext: { value: { tenantId: 'tenant-a' } },
  isAdmin: { value: true },
  canWrite: { value: true },
  canAnalyze: { value: true },
  state: {
    currentUser: {
      id: 'admin-1',
      username: 'admin',
      email: 'admin@example.com',
      display_name: 'Admin User',
      role: 'admin',
      tenant_id: 'tenant-a',
      expires_at: null,
      must_change_password: false,
    },
  },
};

vi.mock('../stores/session', () => ({
  useSession: () => session,
}));

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type', 'icon', 'severity', 'outlined', 'text'],
  template: `
    <button :type="type || 'button'" :disabled="disabled" @click="$emit('click', $event)">
      {{ label }}<slot />
    </button>
  `,
};

const InputTextStub = {
  props: ['modelValue', 'type', 'placeholder', 'disabled'],
  emits: ['update:modelValue'],
  template: `
    <input
      :type="type || 'text'"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="$emit('update:modelValue', $event.target.value)"
    >
  `,
};

const SelectStub = {
  props: ['modelValue', 'options', 'optionLabel', 'optionValue', 'disabled'],
  emits: ['update:modelValue', 'change'],
  template: `
    <select
      :value="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.value); $emit('change', $event)"
    >
      <option v-for="option in options" :key="option[optionValue || 'value']" :value="option[optionValue || 'value']">
        {{ option[optionLabel || 'label'] }}
      </option>
    </select>
  `,
};

const CheckboxStub = {
  props: ['modelValue', 'binary', 'disabled'],
  emits: ['update:modelValue'],
  template: `
    <input
      type="checkbox"
      :checked="Boolean(modelValue)"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.checked)"
    >
  `,
};

function mountPage() {
  return mount(UserManagementPage, {
    global: {
      stubs: {
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        Checkbox: CheckboxStub,
        InputText: InputTextStub,
        Message: { template: '<div><slot /></div>' },
        PageHeader: { template: '<div><slot name="actions" /></div>' },
        Select: SelectStub,
        Tag: { template: '<span><slot /></span>' },
      },
    },
  });
}

describe('UserManagementPage', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    apiPatch.mockReset();
    apiDelete.mockReset();
  });

  it('loads admin users on mount', async () => {
    apiGet.mockResolvedValue({
      users: [
        {
          id: 'user-1',
          username: 'alice',
          email: 'alice@example.com',
          display_name: 'Alice',
          role: 'analyst',
          tenant_id: 'tenant-a',
          expires_at: null,
          must_change_password: false,
          disabled: false,
        },
      ],
    });

    const wrapper = mountPage();
    await flushPromises();

    expect(apiGet).toHaveBeenCalledWith('/api/admin/users');
    expect(wrapper.text()).toContain('alice@example.com');
  });

  it('posts the create payload with role and blank expiry normalized', async () => {
    apiGet.mockResolvedValue({ users: [] });
    apiPost.mockResolvedValue({
      user: {
        id: 'user-2',
        username: 'newuser',
        email: 'newuser@example.com',
        display_name: 'New User',
        role: 'viewer',
        tenant_id: 'tenant-a',
        expires_at: null,
        must_change_password: true,
        disabled: false,
      },
    });

    const wrapper = mountPage();
    await flushPromises();

    const inputs = wrapper.findAll('input');
    await inputs[0]?.setValue('newuser');
    await inputs[1]?.setValue('newuser@example.com');
    await inputs[2]?.setValue('New User');
    await wrapper.find('select').setValue('viewer');
    await inputs[3]?.setValue('TempPass123!');
    await inputs[4]?.setValue('');
    await wrapper.get('[data-testid="create-user-submit"]').trigger('click');

    expect(apiPost).toHaveBeenCalledWith('/api/admin/users', {
      username: 'newuser',
      email: 'newuser@example.com',
      display_name: 'New User',
      role: 'viewer',
      password: 'TempPass123!',
      expires_at: null,
    });
  });

  it('shows api validation errors', async () => {
    apiGet.mockResolvedValue({ users: [] });
    apiPost.mockRejectedValue(new Error('username already exists'));

    const wrapper = mountPage();
    await flushPromises();

    const inputs = wrapper.findAll('input');
    await inputs[0]?.setValue('existing');
    await inputs[1]?.setValue('existing@example.com');
    await inputs[2]?.setValue('Existing');
    await wrapper.find('select').setValue('viewer');
    await inputs[3]?.setValue('TempPass123!');
    await wrapper.get('[data-testid="create-user-submit"]').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('username already exists');
  });
});
