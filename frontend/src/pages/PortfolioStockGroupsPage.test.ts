import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PortfolioStockGroupsPage from './PortfolioStockGroupsPage.vue';

const { apiGet, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiDelete: vi.fn(),
}));

vi.mock('../services/api', () => ({
  apiGet,
  apiDelete,
}));

vi.mock('../stores/session', () => ({
  useSession: () => ({
    apiContext: { value: { tenantId: 'tenant-a', apiToken: 'token-a' } },
    canWrite: { value: true },
  }),
}));

describe('PortfolioStockGroupsPage', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiDelete.mockReset();
    apiGet.mockResolvedValue([{ id: 'group-1', name: 'AI Leaders', tickers: ['NVDA', 'MSFT'] }]);
  });

  it('loads stock groups and deletes one row', async () => {
    const wrapper = mount(PortfolioStockGroupsPage, {
      global: {
        stubs: {
          Button: { props: ['label', 'disabled'], emits: ['click'], template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}<slot /></button>' },
          Message: { template: '<div><slot /></div>' },
          MetricGrid: { props: ['items'], template: '<div>{{ items.length }}</div>' },
          PageHeader: { template: '<div><slot name="actions" /></div>' },
          PortfolioSubnav: { template: '<nav />' },
          StockGroupDialog: { props: ['visible'], emits: ['update:visible', 'saved'], template: '<div />' },
        },
      },
    });

    await flushPromises();
    expect(apiGet).toHaveBeenCalledWith('/api/stock-groups', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(wrapper.text()).toContain('AI Leaders');
    await wrapper.get('[data-testid="stock-group-delete-group-1"]').trigger('click');
    expect(apiDelete).toHaveBeenCalledWith('/api/stock-groups/group-1', { tenantId: 'tenant-a', apiToken: 'token-a' });
  });
});
