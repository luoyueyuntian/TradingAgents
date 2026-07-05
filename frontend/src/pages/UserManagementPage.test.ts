import { mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import UserManagementPage from './UserManagementPage.vue';

const userCrudManagerProps = vi.hoisted(() => vi.fn());

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

vi.mock('../components/UserCrudManager.vue', () => ({
  default: {
    props: ['listPath', 'createPath', 'bulkDeletePath', 'updatePath', 'deletePath', 'resetPasswordPath'],
    template: '<div data-testid="user-crud-manager-stub" />',
    setup(props: Record<string, unknown>) {
      userCrudManagerProps(props);
      return {};
    },
  },
}));

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type', 'icon', 'severity', 'outlined', 'text'],
  template: `
    <button :type="type || 'button'" :disabled="disabled" @click="$emit('click', $event)">
      {{ label }}<slot />
    </button>
  `,
};

function mountPage() {
  return mount(UserManagementPage, {
    global: {
      stubs: {
        Button: ButtonStub,
        PageHeader: { template: '<div><slot name="actions" /></div>' },
      },
    },
  });
}

describe('UserManagementPage', () => {
  beforeEach(() => {
    userCrudManagerProps.mockReset();
  });

  it('passes current-tenant user endpoints into the CRUD manager', async () => {
    const wrapper = mountPage();

    expect(wrapper.find('[data-testid="user-crud-manager-stub"]').exists()).toBe(true);
    expect(userCrudManagerProps).toHaveBeenCalledWith(
      expect.objectContaining({
        listPath: '/api/admin/users',
        createPath: '/api/admin/users',
        bulkDeletePath: '/api/admin/users/bulk-delete',
        updatePath: expect.any(Function),
        deletePath: expect.any(Function),
        resetPasswordPath: expect.any(Function),
      }),
    );
    const props = userCrudManagerProps.mock.calls[0]?.[0] as {
      updatePath: (userId: string) => string;
      deletePath: (userId: string) => string;
      resetPasswordPath: (userId: string) => string;
    };
    expect(props.updatePath('user-7')).toBe('/api/admin/users/user-7');
    expect(props.deletePath('user-7')).toBe('/api/admin/users/user-7');
    expect(props.resetPasswordPath('user-7')).toBe('/api/admin/users/user-7/reset-password');
  });
});
