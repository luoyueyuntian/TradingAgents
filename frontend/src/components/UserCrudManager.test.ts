import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import UserCrudManager from './UserCrudManager.vue';

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
  props: ['label', 'disabled', 'loading', 'type', 'severity', 'outlined', 'text', 'icon'],
  emits: ['click'],
  template: `
    <button
      v-bind="$attrs"
      :type="type || 'button'"
      :disabled="disabled"
      @click="$emit('click', $event)"
    >
      {{ label }}<slot />
    </button>
  `,
};

const InputTextStub = {
  props: ['modelValue', 'type', 'placeholder', 'disabled', 'readonly'],
  emits: ['update:modelValue'],
  template: `
    <input
      v-bind="$attrs"
      :type="type || 'text'"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      :readonly="readonly"
      @input="$emit('update:modelValue', $event.target.value)"
    >
  `,
};

const SelectStub = {
  props: ['modelValue', 'options', 'optionLabel', 'optionValue', 'disabled'],
  emits: ['update:modelValue'],
  template: `
    <select
      v-bind="$attrs"
      :value="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.value)"
    >
      <option v-for="option in options" :key="option[optionValue || 'value']" :value="option[optionValue || 'value']">
        {{ option[optionLabel || 'label'] }}
      </option>
    </select>
  `,
};

function makeUser(overrides: Record<string, unknown> = {}) {
  return {
    id: 'user-1',
    username: 'alice',
    email: 'alice@example.com',
    display_name: 'Alice Analyst',
    role: 'analyst',
    tenant_id: 'tenant-a',
    expires_at: null,
    disabled: false,
    must_change_password: false,
    created_at: 1_783_353_600_000,
    updated_at: 1_783_353_600_000,
    last_login_at: null,
    ...overrides,
  };
}

function mountComponent() {
  return mount(UserCrudManager, {
    props: {
      listPath: '/api/admin/users',
      createPath: '/api/admin/users',
      bulkDeletePath: '/api/admin/users/bulk-delete',
      updatePath: (userId: string) => `/api/admin/users/${userId}`,
      deletePath: (userId: string) => `/api/admin/users/${userId}`,
      resetPasswordPath: (userId: string) => `/api/admin/users/${userId}/reset-password`,
    },
    global: {
      stubs: {
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        Dialog: { props: ['visible'], template: '<div v-if="visible"><slot /><slot name="footer" /></div>' },
        InputText: InputTextStub,
        DateTimeInput: InputTextStub,
        Message: { template: '<div><slot /></div>' },
        Select: SelectStub,
      },
    },
  });
}

describe('UserCrudManager', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    apiPatch.mockReset();
    apiDelete.mockReset();
  });

  it('loads users with search filters and deleted_scope=active', async () => {
    apiGet.mockResolvedValue({ users: [] });
    const wrapper = mountComponent();
    await flushPromises();

    await wrapper.get('[data-testid="filter-name"]').setValue('alice');
    await wrapper.get('[data-testid="search-users"]').trigger('click');
    await flushPromises();

    expect(apiGet).toHaveBeenLastCalledWith('/api/admin/users?status=all&deleted_scope=active&name=alice');
  });

  it('shows a temporary password for new accounts without offering account password resets', async () => {
    apiGet.mockResolvedValue({ users: [makeUser()] });
    apiPost
      .mockResolvedValueOnce({
        user: makeUser({ id: 'user-2', username: 'newuser', email: 'newuser@example.com' }),
        temporary_password: 'TempCreate123!',
      })
      .mockResolvedValueOnce({
        user: makeUser(),
        temporary_password: 'TempReset123!',
      });

    const wrapper = mountComponent();
    await flushPromises();

    await wrapper.get('[data-testid="open-create-user"]').trigger('click');
    await wrapper.get('[data-testid="user-form-username"]').setValue('newuser');
    await wrapper.get('[data-testid="user-form-display-name"]').setValue('New User');
    await wrapper.get('[data-testid="user-form-email"]').setValue('newuser@example.com');
    await wrapper.get('[data-testid="submit-user-form"]').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('TempCreate123!');

    expect(wrapper.find('[data-testid="reset-password-user-1"]').exists()).toBe(false);
  });

  it('adds an existing account by email without showing a temporary password', async () => {
    apiGet.mockResolvedValue({ users: [] });
    apiPost.mockResolvedValue({ user: makeUser(), temporary_password: '' });
    const wrapper = mountComponent();
    await flushPromises();
    await wrapper.get('[data-testid="open-add-member"]').trigger('click');
    expect(wrapper.find('[data-testid="user-form-username"]').exists()).toBe(false);
    await wrapper.get('[data-testid="user-form-email"]').setValue('alice@example.com');
    await wrapper.get('[data-testid="submit-user-form"]').trigger('click');
    await flushPromises();
    expect(apiPost).toHaveBeenCalledWith('/api/admin/users/memberships', {
      email: 'alice@example.com', role: 'viewer', expires_at: null,
    });
    expect(wrapper.text()).not.toContain('TempCreate123!');
  });

  it('sends partial bulk delete requests and refreshes the list', async () => {
    apiGet.mockResolvedValue({
      users: [
        makeUser(),
        makeUser({ id: 'user-2', username: 'bravo', email: 'bravo@example.com' }),
      ],
    });
    apiPost.mockResolvedValue({
      deleted_ids: ['user-2'],
      failed: [{ user_id: 'user-1', detail: 'Cannot remove the last active admin from tenant' }],
    });

    const wrapper = mountComponent();
    await flushPromises();

    await wrapper.get('[data-testid="select-user-user-1"]').setValue(true);
    await wrapper.get('[data-testid="select-user-user-2"]').setValue(true);
    await wrapper.get('[data-testid="open-bulk-delete"]').trigger('click');
    await wrapper.get('[data-testid="confirm-bulk-delete"]').trigger('click');
    await flushPromises();

    expect(apiPost).toHaveBeenCalledWith('/api/admin/users/bulk-delete', {
      user_ids: ['user-1', 'user-2'],
    });
  });
});
