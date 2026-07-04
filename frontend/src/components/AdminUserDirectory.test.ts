import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import AdminUserDirectory from './AdminUserDirectory.vue';

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

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type', 'icon', 'severity', 'outlined', 'text', 'dataTestid'],
  emits: ['click'],
  template: `
    <button
      :type="type || 'button'"
      :disabled="disabled"
      :data-testid="dataTestid"
      @click="$emit('click', $event)"
    >
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

function mountComponent() {
  return mount(AdminUserDirectory, {
    props: {
      listPath: '/api/admin/tenants/tenant-a/users',
      createPath: '/api/admin/tenants/tenant-a/users',
      updatePath: (userId: string) => `/api/admin/tenants/tenant-a/users/${userId}`,
      deletePath: (userId: string) => `/api/admin/tenants/tenant-a/users/${userId}`,
      readOnly: false,
    },
    global: {
      stubs: {
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        InputText: InputTextStub,
        Message: { template: '<div><slot /></div>' },
        Select: SelectStub,
      },
    },
  });
}

describe('AdminUserDirectory', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    apiPatch.mockReset();
    apiDelete.mockReset();
  });

  it('loads users from the caller-provided list path on mount', async () => {
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

    const wrapper = mountComponent();
    await flushPromises();

    expect(apiGet).toHaveBeenCalledWith('/api/admin/tenants/tenant-a/users');
    expect(wrapper.text()).toContain('alice@example.com');
  });

  it('uses the caller-provided create, update, and delete paths for row actions', async () => {
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
    apiPatch.mockResolvedValue({
      user: {
        id: 'user-1',
        username: 'alice',
        email: 'alice@example.com',
        display_name: 'Alice Updated',
        role: 'admin',
        tenant_id: 'tenant-a',
        expires_at: null,
        must_change_password: false,
        disabled: false,
      },
    });
    apiDelete.mockResolvedValue({});

    const wrapper = mountComponent();
    await flushPromises();

    const inputs = wrapper.findAll('input');
    await inputs[0]?.setValue('newuser');
    await inputs[1]?.setValue('newuser@example.com');
    await inputs[2]?.setValue('New User');
    await wrapper.find('select').setValue('viewer');
    await inputs[3]?.setValue('TempPass123!');
    await wrapper.get('[data-testid="create-user-submit"]').trigger('click');
    await flushPromises();

    expect(apiPost).toHaveBeenCalledWith('/api/admin/tenants/tenant-a/users', {
      username: 'newuser',
      email: 'newuser@example.com',
      display_name: 'New User',
      role: 'viewer',
      password: 'TempPass123!',
      expires_at: null,
    });

    await wrapper.findAll('select')[1]!.setValue('admin');
    await wrapper.get('[data-testid="save-user-user-1"]').trigger('click');
    await flushPromises();

    expect(apiPatch).toHaveBeenCalledWith(
      '/api/admin/tenants/tenant-a/users/user-1',
      expect.objectContaining({
        role: 'admin',
        expires_at: null,
        disabled: false,
      }),
    );

    await wrapper.get('[data-testid="delete-user-user-1"]').trigger('click');
    await flushPromises();

    expect(apiDelete).toHaveBeenCalledWith('/api/admin/tenants/tenant-a/users/user-1');
  });

  it('renders the directory in read-only mode for archived tenants', async () => {
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

    const wrapper = mount(AdminUserDirectory, {
      props: {
        listPath: '/api/admin/tenants/tenant-a/users',
        createPath: '/api/admin/tenants/tenant-a/users',
        updatePath: (userId: string) => `/api/admin/tenants/tenant-a/users/${userId}`,
        deletePath: (userId: string) => `/api/admin/tenants/tenant-a/users/${userId}`,
        readOnly: true,
      },
      global: {
        stubs: {
          Button: ButtonStub,
          Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
          InputText: InputTextStub,
          Message: { template: '<div><slot /></div>' },
          Select: SelectStub,
        },
      },
    });
    await flushPromises();

    expect(wrapper.find('[data-testid="create-user-submit"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="save-user-user-1"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="delete-user-user-1"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="reset-password-user-1"]').exists()).toBe(false);
    expect(wrapper.findAll('input').every((input) => input.element.disabled)).toBe(true);
    expect(wrapper.findAll('select').every((select) => select.element.disabled)).toBe(true);
    expect(apiPost).not.toHaveBeenCalled();
    expect(apiPatch).not.toHaveBeenCalled();
    expect(apiDelete).not.toHaveBeenCalled();
  });
});
