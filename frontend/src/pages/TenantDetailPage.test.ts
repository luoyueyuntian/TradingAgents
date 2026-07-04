import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import TenantDetailPage from './TenantDetailPage.vue';

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

vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: {
      tenantId: 'tenant-a',
    },
  }),
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

function mountPage() {
  return mount(TenantDetailPage, {
    global: {
      stubs: {
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        InputText: InputTextStub,
        Message: { template: '<div><slot /></div>' },
        PageHeader: { template: '<div><slot name="actions" /></div>' },
        Select: SelectStub,
      },
    },
  });
}

describe('TenantDetailPage', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    apiPatch.mockReset();
    apiDelete.mockReset();
  });

  it('loads tenant metadata and tenant-scoped users on mount', async () => {
    apiGet
      .mockResolvedValueOnce({
        tenant: {
          id: 'tenant-row-1',
          tenant_id: 'tenant-a',
          display_name: 'Tenant A',
          disabled: false,
          archived: false,
          user_count: 2,
          active_admin_count: 1,
          created_at: '2026-07-04T08:00:00Z',
          updated_at: '2026-07-04T09:00:00Z',
        },
      })
      .mockResolvedValueOnce({
        users: [
          {
            id: 'user-1',
            username: 'alice',
            email: 'alice@example.com',
            display_name: 'Alice',
            role: 'admin',
            tenant_id: 'tenant-a',
            expires_at: null,
            must_change_password: false,
            disabled: false,
          },
        ],
      });

    const wrapper = mountPage();
    await flushPromises();

    expect(apiGet).toHaveBeenNthCalledWith(1, '/api/admin/tenants/tenant-a');
    expect(apiGet).toHaveBeenNthCalledWith(2, '/api/admin/tenants/tenant-a/users');
    expect(wrapper.text()).toContain('Tenant A');
    expect(wrapper.text()).toContain('alice@example.com');
  });

  it('patches tenant state toggles against the tenant detail endpoint', async () => {
    apiGet
      .mockResolvedValueOnce({
        tenant: {
          id: 'tenant-row-1',
          tenant_id: 'tenant-a',
          display_name: 'Tenant A',
          disabled: false,
          archived: false,
          user_count: 2,
          active_admin_count: 1,
          created_at: '2026-07-04T08:00:00Z',
          updated_at: '2026-07-04T09:00:00Z',
        },
      })
      .mockResolvedValueOnce({ users: [] })
      .mockResolvedValueOnce({
        tenant: {
          id: 'tenant-row-1',
          tenant_id: 'tenant-a',
          display_name: 'Tenant A',
          disabled: true,
          archived: false,
          user_count: 2,
          active_admin_count: 1,
          created_at: '2026-07-04T08:00:00Z',
          updated_at: '2026-07-04T09:30:00Z',
        },
      })
      .mockResolvedValueOnce({ users: [] });
    apiPatch.mockResolvedValue({
      tenant: {
        id: 'tenant-row-1',
        tenant_id: 'tenant-a',
        display_name: 'Tenant A',
        disabled: true,
        archived: false,
        user_count: 2,
        active_admin_count: 1,
        created_at: '2026-07-04T08:00:00Z',
        updated_at: '2026-07-04T09:30:00Z',
      },
    });

    const wrapper = mountPage();
    await flushPromises();

    await wrapper.get('[data-testid="toggle-tenant-disabled"]').trigger('click');
    await flushPromises();

    expect(apiPatch).toHaveBeenCalledWith('/api/admin/tenants/tenant-a', { disabled: true });
  });
});
