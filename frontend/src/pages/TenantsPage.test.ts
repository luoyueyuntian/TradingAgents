import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import TenantsPage from './TenantsPage.vue';

const { apiGet, apiPost, apiPatch } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
}));

const push = vi.fn();

vi.mock('../services/api', () => ({
  apiGet,
  apiPost,
  apiPatch,
}));

vi.mock('vue-router', () => ({
  useRouter: () => ({ push }),
}));

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type', 'icon', 'severity', 'outlined', 'text'],
  emits: ['click'],
  template: `
    <button
      :type="type || 'button'"
      :disabled="disabled"
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

function mountPage() {
  return mount(TenantsPage, {
    global: {
      stubs: {
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        InputText: InputTextStub,
        Message: { template: '<div><slot /></div>' },
        PageHeader: { template: '<div><slot name="actions" /></div>' },
      },
    },
  });
}

describe('TenantsPage', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    apiPatch.mockReset();
    push.mockReset();
  });

  it('loads the tenant list on mount', async () => {
    apiGet.mockResolvedValue({
      tenants: [
        {
          id: 'tenant-row-1',
          tenant_id: 'tenant-a',
          display_name: 'Tenant A',
          disabled: false,
          archived: false,
          user_count: 4,
          active_admin_count: 2,
          created_at: '2026-07-04T08:00:00Z',
          updated_at: '2026-07-04T09:00:00Z',
        },
      ],
    });

    const wrapper = mountPage();
    await flushPromises();

    expect(apiGet).toHaveBeenCalledWith('/api/admin/tenants');
    expect(wrapper.text()).toContain('Tenant A');
    expect(wrapper.text()).toContain('tenant-a');
  });

  it('posts the create-tenant payload with initial admin fields', async () => {
    apiGet.mockResolvedValue({ tenants: [] });
    apiPost.mockResolvedValue({
      tenant: {
        id: 'tenant-row-2',
        tenant_id: 'tenant-b',
        display_name: 'Tenant B',
        disabled: false,
        archived: false,
        user_count: 1,
        active_admin_count: 1,
        created_at: '2026-07-04T10:00:00Z',
        updated_at: '2026-07-04T10:00:00Z',
      },
    });

    const wrapper = mountPage();
    await flushPromises();

    const inputs = wrapper.findAll('input');
    await inputs[0]?.setValue('tenant-b');
    await inputs[1]?.setValue('Tenant B');
    await inputs[2]?.setValue('bootstrap-admin');
    await inputs[3]?.setValue('admin@example.com');
    await inputs[4]?.setValue('Bootstrap Admin');
    await inputs[5]?.setValue('TempPass123!');
    await wrapper.get('[data-testid="create-tenant-submit"]').trigger('click');

    expect(apiPost).toHaveBeenCalledWith('/api/admin/tenants', {
      tenant_id: 'tenant-b',
      display_name: 'Tenant B',
      admin: {
        username: 'bootstrap-admin',
        email: 'admin@example.com',
        display_name: 'Bootstrap Admin',
        password: 'TempPass123!',
      },
    });
  });

  it('sends patch requests for disable, enable, and archive actions', async () => {
    apiGet.mockResolvedValue({
      tenants: [
        {
          id: 'tenant-row-1',
          tenant_id: 'tenant-a',
          display_name: 'Tenant A',
          disabled: false,
          archived: false,
          user_count: 4,
          active_admin_count: 2,
          created_at: '2026-07-04T08:00:00Z',
          updated_at: '2026-07-04T09:00:00Z',
        },
        {
          id: 'tenant-row-2',
          tenant_id: 'tenant-b',
          display_name: 'Tenant B',
          disabled: true,
          archived: false,
          user_count: 3,
          active_admin_count: 1,
          created_at: '2026-07-04T08:00:00Z',
          updated_at: '2026-07-04T09:00:00Z',
        },
      ],
    });
    apiPatch.mockResolvedValue({
      tenant: {
        id: 'tenant-row-1',
        tenant_id: 'tenant-a',
        display_name: 'Tenant A',
        disabled: true,
        archived: false,
        user_count: 4,
        active_admin_count: 2,
        created_at: '2026-07-04T08:00:00Z',
        updated_at: '2026-07-04T09:30:00Z',
      },
    });

    const wrapper = mountPage();
    await flushPromises();

    const toggleButtons = wrapper.findAll('[data-testid^="toggle-tenant-"]');

    await toggleButtons[0]!.trigger('click');
    await flushPromises();
    await wrapper.findAll('[data-testid^="toggle-tenant-"]')[1]!.trigger('click');
    await flushPromises();
    await wrapper.get('[data-testid="archive-tenant-tenant-a"]').trigger('click');
    await flushPromises();

    expect(apiPatch).toHaveBeenNthCalledWith(1, '/api/admin/tenants/tenant-a', { disabled: true });
    expect(apiPatch).toHaveBeenNthCalledWith(2, '/api/admin/tenants/tenant-b', { disabled: false });
    expect(apiPatch).toHaveBeenNthCalledWith(3, '/api/admin/tenants/tenant-a', { archived: true });
  });
});
