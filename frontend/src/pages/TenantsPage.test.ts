import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import TenantsPage from './TenantsPage.vue';

const { formatDateTime, formatDateTimeInputValue } = vi.hoisted(() => ({
  formatDateTime: vi.fn((value: unknown) => `LOCAL:${String(value)}`),
  formatDateTimeInputValue: vi.fn((value: unknown) => {
    if (!value) {
      return '';
    }
    const date = new Date(Number(value));
    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');
    const hours = String(date.getUTCHours()).padStart(2, '0');
    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
    return `${year}-${month}-${day}T${hours}:${minutes}`;
  }),
}));

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

vi.mock('../utils/format', async () => {
  const actual = await vi.importActual<typeof import('../utils/format')>('../utils/format');
  return {
    ...actual,
    formatDateTime,
    formatDateTimeInputValue,
  };
});

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type'],
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
  props: ['modelValue', 'type', 'placeholder', 'disabled'],
  emits: ['update:modelValue'],
  template: `
    <input
      v-bind="$attrs"
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
        Dialog: { props: ['visible'], template: '<div v-if="visible"><slot /></div>' },
        InputText: InputTextStub,
        DateTimeInput: InputTextStub,
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
    formatDateTime.mockClear();
    formatDateTimeInputValue.mockClear();
  });

  it('loads the tenant list on mount', async () => {
    apiGet.mockResolvedValue({
      tenants: [
        {
          id: 'tenant-row-1',
          tenant_id: 'tenant-a',
          display_name: 'Tenant A',
          disabled: false,
          expires_at: null,
          status: 'active',
          user_count: 4,
          active_admin_count: 2,
          created_at: 1_783_353_600_000,
          updated_at: 1_783_357_200_000,
        },
      ],
    });

    const wrapper = mountPage();
    await flushPromises();

    expect(apiGet).toHaveBeenCalledWith('/api/admin/tenants');
    expect(wrapper.text()).toContain('Tenant A');
    expect(wrapper.text()).toContain('tenant-a');
    expect(wrapper.text()).toContain('LOCAL:1783353600000');
  });

  it('sends filtered search params from the filter bar', async () => {
    apiGet.mockResolvedValue({ tenants: [] });

    const wrapper = mountPage();
    await flushPromises();

    await wrapper.get('[data-testid="tenant-filter-name"]').setValue('gamma');
    await wrapper.get('[data-testid="tenant-filter-status"]').setValue('expired');
    await wrapper.get('[data-testid="tenant-filter-created-from"]').setValue('2026-07-08');
    await wrapper.get('[data-testid="tenant-filter-created-to"]').setValue('2026-07-11');
    await wrapper.get('[data-testid="tenant-filter-submit"]').trigger('click');

    const createdFrom = new Date('2026-07-08T00:00').getTime();
    const createdTo = new Date('2026-07-11T23:59:59.999').getTime();
    expect(apiGet).toHaveBeenNthCalledWith(
      2,
      `/api/admin/tenants?name=gamma&status=expired&created_from=${createdFrom}&created_to=${createdTo}`,
    );
  });

  it('posts the create-tenant payload and opens the created tenant detail route', async () => {
    apiGet.mockResolvedValue({ tenants: [] });
    apiPost.mockResolvedValue({
      tenant: {
        id: 'tenant-row-2',
        tenant_id: 'tenant-b',
        display_name: 'Tenant B',
        disabled: false,
        expires_at: 1_783_612_800_000,
        status: 'active',
        user_count: 0,
        active_admin_count: 0,
        created_at: 1_783_353_600_000,
        updated_at: 1_783_353_600_000,
      },
    });

    const wrapper = mountPage();
    await flushPromises();

    await wrapper.get('[data-testid="open-create-tenant"]').trigger('click');
    await wrapper.get('[data-testid="tenant-form-display-name"]').setValue('Tenant B');
    await wrapper.get('[data-testid="tenant-form-expires-at"]').setValue('2026-07-07T00:00');
    await wrapper.get('[data-testid="tenant-dialog-submit"]').trigger('click');

    expect(apiPost).toHaveBeenCalledWith('/api/admin/tenants', {
      display_name: 'Tenant B',
      expires_at: new Date('2026-07-07T00:00').getTime(),
    });
    expect(push).toHaveBeenCalledWith({ name: 'tenant-detail', params: { tenantId: 'tenant-b' } });
  });

  it('patches the edit payload from the shared tenant dialog', async () => {
    apiGet.mockResolvedValue({
      tenants: [
        {
          id: 'tenant-row-1',
          tenant_id: 'tenant-a',
          display_name: 'Tenant A',
          disabled: false,
          expires_at: 1_783_612_800_000,
          status: 'active',
          user_count: 4,
          active_admin_count: 2,
          created_at: 1_783_353_600_000,
          updated_at: 1_783_357_200_000,
        },
      ],
    });
    apiPatch.mockResolvedValue({
      tenant: {
        id: 'tenant-row-1',
        tenant_id: 'tenant-a',
        display_name: 'Tenant A Updated',
        disabled: false,
        expires_at: 1_783_699_200_000,
        status: 'active',
        user_count: 4,
        active_admin_count: 2,
        created_at: 1_783_353_600_000,
        updated_at: 1_783_357_200_000,
      },
    });

    const wrapper = mountPage();
    await flushPromises();

    await wrapper.get('[data-testid="edit-tenant-tenant-a"]').trigger('click');
    await wrapper.get('[data-testid="tenant-form-display-name"]').setValue('Tenant A Updated');
    await wrapper.get('[data-testid="tenant-form-expires-at"]').setValue('2026-07-08T00:00');
    await wrapper.get('[data-testid="tenant-dialog-submit"]').trigger('click');

    expect(apiPatch).toHaveBeenCalledWith('/api/admin/tenants/tenant-a', {
      display_name: 'Tenant A Updated',
      expires_at: new Date('2026-07-08T00:00').getTime(),
    });
  });

  it('allows clearing an existing tenant expiry from the edit dialog', async () => {
    apiGet.mockResolvedValue({
      tenants: [
        {
          id: 'tenant-row-1',
          tenant_id: 'tenant-a',
          display_name: 'Tenant A',
          disabled: false,
          expires_at: 1_783_612_800_000,
          status: 'active',
          user_count: 4,
          active_admin_count: 2,
          created_at: 1_783_353_600_000,
          updated_at: 1_783_357_200_000,
        },
      ],
    });
    apiPatch.mockResolvedValue({
      tenant: {
        id: 'tenant-row-1',
        tenant_id: 'tenant-a',
        display_name: 'Tenant A',
        disabled: false,
        expires_at: null,
        status: 'active',
        user_count: 4,
        active_admin_count: 2,
        created_at: 1_783_353_600_000,
        updated_at: 1_783_357_200_000,
      },
    });

    const wrapper = mountPage();
    await flushPromises();

    await wrapper.get('[data-testid="edit-tenant-tenant-a"]').trigger('click');
    await wrapper.get('[data-testid="tenant-form-expires-at"]').setValue('');
    await wrapper.get('[data-testid="tenant-dialog-submit"]').trigger('click');

    expect(apiPatch).toHaveBeenCalledWith('/api/admin/tenants/tenant-a', {
      display_name: 'Tenant A',
      expires_at: null,
    });
  });

  it('sends the selected active tenant ids to the batch-disable endpoint', async () => {
    apiGet.mockResolvedValue({
      tenants: [
        {
          id: 'tenant-row-1',
          tenant_id: 'tenant-a',
          display_name: 'Tenant A',
          disabled: false,
          expires_at: null,
          status: 'active',
          user_count: 4,
          active_admin_count: 2,
          created_at: 1_783_353_600_000,
          updated_at: 1_783_357_200_000,
        },
        {
          id: 'tenant-row-2',
          tenant_id: 'tenant-b',
          display_name: 'Tenant B',
          disabled: true,
          expires_at: null,
          status: 'disabled',
          user_count: 1,
          active_admin_count: 1,
          created_at: 1_783_353_600_000,
          updated_at: 1_783_357_200_000,
        },
      ],
    });
    apiPost.mockResolvedValue({
      updated_count: 1,
      skipped_count: 0,
      skipped_tenant_ids: [],
    });

    const wrapper = mountPage();
    await flushPromises();

    await wrapper.get('[data-testid="tenant-select-tenant-a"]').setValue(true);
    await wrapper.get('[data-testid="batch-disable-tenants"]').trigger('click');

    expect(apiPost).toHaveBeenCalledWith('/api/admin/tenants/batch-disable', {
      tenant_ids: ['tenant-a'],
    });
  });
});
