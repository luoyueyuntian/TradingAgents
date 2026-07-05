import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { reactive } from 'vue';

import TenantDetailPage from './TenantDetailPage.vue';

const { formatDateTime } = vi.hoisted(() => ({
  formatDateTime: vi.fn((value: unknown) => `LOCAL:${String(value)}`),
}));

const { apiGet, apiPatch } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
}));

const route = reactive({
  params: {
    tenantId: 'tenant-a',
  },
});

const adminUserDirectoryProps = vi.hoisted(() => vi.fn());
const adminUserDirectoryLoadUsers = vi.hoisted(() => vi.fn());

vi.mock('../services/api', () => ({
  apiGet,
  apiPatch,
}));

vi.mock('vue-router', () => ({
  useRoute: () => route,
}));

vi.mock('../utils/format', async () => {
  const actual = await vi.importActual<typeof import('../utils/format')>('../utils/format');
  return {
    ...actual,
    formatDateTime,
  };
});

vi.mock('../components/AdminUserDirectory.vue', () => ({
  default: {
    props: ['listPath', 'createPath', 'updatePath', 'deletePath', 'readOnly'],
    template: '<div data-testid="admin-user-directory-stub" />',
    setup(props: Record<string, unknown>, { expose }: { expose: (value: unknown) => void }) {
      adminUserDirectoryProps(props);
      expose({
        loadUsers: adminUserDirectoryLoadUsers,
      });
      return {};
    },
  },
}));

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

function mountPage() {
  return mount(TenantDetailPage, {
    global: {
      stubs: {
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        Message: { template: '<div><slot /></div>' },
        PageHeader: { template: '<div><slot name="actions" /></div>' },
      },
    },
  });
}

let mountedWrapper: ReturnType<typeof mountPage> | null = null;

describe('TenantDetailPage', () => {
  beforeEach(() => {
    route.params.tenantId = 'tenant-a';
    apiGet.mockReset();
    apiPatch.mockReset();
    adminUserDirectoryProps.mockReset();
    adminUserDirectoryLoadUsers.mockReset();
    formatDateTime.mockClear();
  });

  afterEach(() => {
    mountedWrapper?.unmount();
    mountedWrapper = null;
  });

  it('loads tenant metadata and configures tenant-scoped users on mount', async () => {
    apiGet.mockResolvedValue({
      tenant: {
        id: 'tenant-row-1',
        tenant_id: 'tenant-a',
        display_name: 'Tenant A',
        disabled: false,
        expires_at: 1_783_612_800_000,
        status: 'active',
        user_count: 2,
        active_admin_count: 1,
        created_at: 1_783_353_600_000,
        updated_at: 1_783_357_200_000,
      },
    });

    const wrapper = mountPage();
    mountedWrapper = wrapper;
    await flushPromises();

    expect(apiGet).toHaveBeenCalledWith('/api/admin/tenants/tenant-a');
    expect(wrapper.text()).toContain('Tenant A');
    expect(wrapper.text()).toContain('LOCAL:1783612800000');
    expect(wrapper.find('[data-testid="admin-user-directory-stub"]').exists()).toBe(true);
    expect(adminUserDirectoryProps).toHaveBeenCalledWith(
      expect.objectContaining({
        listPath: '/api/admin/tenants/tenant-a/users',
        createPath: '/api/admin/tenants/tenant-a/users',
        readOnly: false,
      }),
    );
  });

  it('reloads tenant metadata and tenant-scoped users when the tenantId route param changes', async () => {
    apiGet
      .mockResolvedValueOnce({
        tenant: {
          id: 'tenant-row-1',
          tenant_id: 'tenant-a',
          display_name: 'Tenant A',
          disabled: false,
          expires_at: null,
          status: 'active',
          user_count: 2,
          active_admin_count: 1,
          created_at: 1_783_353_600_000,
          updated_at: 1_783_357_200_000,
        },
      })
      .mockResolvedValueOnce({
        tenant: {
          id: 'tenant-row-2',
          tenant_id: 'tenant-b',
          display_name: 'Tenant B',
          disabled: false,
          expires_at: null,
          status: 'active',
          user_count: 3,
          active_admin_count: 1,
          created_at: 1_783_353_600_000,
          updated_at: 1_783_357_200_000,
        },
      });

    const wrapper = mountPage();
    mountedWrapper = wrapper;
    await flushPromises();

    route.params.tenantId = 'tenant-b';
    await flushPromises();

    expect(apiGet).toHaveBeenNthCalledWith(1, '/api/admin/tenants/tenant-a');
    expect(apiGet).toHaveBeenNthCalledWith(2, '/api/admin/tenants/tenant-b');
    expect(adminUserDirectoryLoadUsers).toHaveBeenCalledTimes(1);
    expect(adminUserDirectoryProps).toHaveBeenLastCalledWith(
      expect.objectContaining({
        listPath: '/api/admin/tenants/tenant-b/users',
      }),
    );
    expect(wrapper.text()).toContain('Tenant B');
  });

  it('patches the disable toggle against the tenant detail endpoint', async () => {
    apiGet.mockResolvedValue({
      tenant: {
        id: 'tenant-row-1',
        tenant_id: 'tenant-a',
        display_name: 'Tenant A',
        disabled: false,
        expires_at: null,
        status: 'active',
        user_count: 2,
        active_admin_count: 1,
        created_at: 1_783_353_600_000,
        updated_at: 1_783_357_200_000,
      },
    });
    apiPatch.mockResolvedValue({
      tenant: {
        id: 'tenant-row-1',
        tenant_id: 'tenant-a',
        display_name: 'Tenant A',
        disabled: true,
        expires_at: null,
        status: 'disabled',
        user_count: 2,
        active_admin_count: 1,
        created_at: 1_783_353_600_000,
        updated_at: 1_783_357_200_000,
      },
    });

    const wrapper = mountPage();
    mountedWrapper = wrapper;
    await flushPromises();

    await wrapper.get('[data-testid="toggle-tenant-disabled"]').trigger('click');
    await flushPromises();

    expect(apiPatch).toHaveBeenCalledWith('/api/admin/tenants/tenant-a', { disabled: true });
  });

  it('makes the user directory read-only for expired tenants and removes archive controls', async () => {
    apiGet.mockResolvedValue({
      tenant: {
        id: 'tenant-row-1',
        tenant_id: 'tenant-a',
        display_name: 'Tenant A',
        disabled: false,
        expires_at: 1,
        status: 'expired',
        user_count: 2,
        active_admin_count: 1,
        created_at: 1_783_353_600_000,
        updated_at: 1_783_357_200_000,
      },
    });

    const wrapper = mountPage();
    mountedWrapper = wrapper;
    await flushPromises();

    expect(wrapper.find('[data-testid="archive-tenant"]').exists()).toBe(false);
    expect(adminUserDirectoryProps).toHaveBeenLastCalledWith(
      expect.objectContaining({
        readOnly: true,
      }),
    );
  });
});
