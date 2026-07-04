import { flushPromises, mount } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { reactive } from 'vue';

import TenantDetailPage from './TenantDetailPage.vue';

const { apiGet, apiPost, apiPatch, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
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
  apiPost,
  apiPatch,
  apiDelete,
}));

vi.mock('vue-router', () => ({
  useRoute: () => route,
}));

vi.mock('../components/AdminUserDirectory.vue', () => ({
  default: {
    props: ['listPath', 'createPath', 'updatePath', 'deletePath'],
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
    apiPost.mockReset();
    apiPatch.mockReset();
    apiDelete.mockReset();
    adminUserDirectoryProps.mockReset();
    adminUserDirectoryLoadUsers.mockReset();
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
        archived: false,
        user_count: 2,
        active_admin_count: 1,
        created_at: '2026-07-04T08:00:00Z',
        updated_at: '2026-07-04T09:00:00Z',
      },
    });

    const wrapper = mountPage();
    mountedWrapper = wrapper;
    await flushPromises();

    expect(apiGet).toHaveBeenCalledWith('/api/admin/tenants/tenant-a');
    expect(wrapper.text()).toContain('Tenant A');
    expect(wrapper.find('[data-testid="admin-user-directory-stub"]').exists()).toBe(true);
    expect(adminUserDirectoryProps).toHaveBeenCalledWith(
      expect.objectContaining({
        listPath: '/api/admin/tenants/tenant-a/users',
        createPath: '/api/admin/tenants/tenant-a/users',
        updatePath: expect.any(Function),
        deletePath: expect.any(Function),
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
          archived: false,
          user_count: 2,
          active_admin_count: 1,
          created_at: '2026-07-04T08:00:00Z',
          updated_at: '2026-07-04T09:00:00Z',
        },
      })
      .mockResolvedValue({
        tenant: {
          id: 'tenant-row-2',
          tenant_id: 'tenant-b',
          display_name: 'Tenant B',
          disabled: false,
          archived: false,
          user_count: 3,
          active_admin_count: 1,
          created_at: '2026-07-04T10:00:00Z',
          updated_at: '2026-07-04T11:00:00Z',
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

  it('refreshes both tenant metadata and the tenant-scoped user list from the page action', async () => {
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
        tenant: {
          id: 'tenant-row-1',
          tenant_id: 'tenant-a',
          display_name: 'Tenant A Reloaded',
          disabled: false,
          archived: false,
          user_count: 2,
          active_admin_count: 1,
          created_at: '2026-07-04T08:00:00Z',
          updated_at: '2026-07-04T09:30:00Z',
        },
      });

    const wrapper = mountPage();
    mountedWrapper = wrapper;
    await flushPromises();

    await wrapper.find('button').trigger('click');
    await flushPromises();

    expect(apiGet).toHaveBeenNthCalledWith(1, '/api/admin/tenants/tenant-a');
    expect(apiGet).toHaveBeenNthCalledWith(2, '/api/admin/tenants/tenant-a');
    expect(adminUserDirectoryLoadUsers).toHaveBeenCalledTimes(1);
    expect(wrapper.text()).toContain('Tenant A Reloaded');
  });

  it('patches tenant state toggles against the tenant detail endpoint', async () => {
    apiGet.mockResolvedValue({
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
    });
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
    mountedWrapper = wrapper;
    await flushPromises();

    await wrapper.get('[data-testid="toggle-tenant-disabled"]').trigger('click');
    await flushPromises();

    expect(apiPatch).toHaveBeenCalledWith('/api/admin/tenants/tenant-a', { disabled: true });
  });

  it('sends archived false when unarchiving from the tenant detail page', async () => {
    apiGet.mockResolvedValue({
      tenant: {
        id: 'tenant-row-1',
        tenant_id: 'tenant-a',
        display_name: 'Tenant A',
        disabled: false,
        archived: true,
        user_count: 2,
        active_admin_count: 1,
        created_at: '2026-07-04T08:00:00Z',
        updated_at: '2026-07-04T09:00:00Z',
      },
    });
    apiPatch.mockResolvedValue({
      tenant: {
        id: 'tenant-row-1',
        tenant_id: 'tenant-a',
        display_name: 'Tenant A',
        disabled: false,
        archived: false,
        user_count: 2,
        active_admin_count: 1,
        created_at: '2026-07-04T08:00:00Z',
        updated_at: '2026-07-04T09:30:00Z',
      },
    });

    const wrapper = mountPage();
    mountedWrapper = wrapper;
    await flushPromises();

    await wrapper.get('[data-testid="archive-tenant"]').trigger('click');
    await flushPromises();

    expect(apiPatch).toHaveBeenCalledWith('/api/admin/tenants/tenant-a', { archived: false });
  });
});
