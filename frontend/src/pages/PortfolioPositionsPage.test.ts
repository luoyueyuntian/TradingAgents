import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PortfolioPositionsPage from './PortfolioPositionsPage.vue';

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

describe('PortfolioPositionsPage', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiDelete.mockReset();
    apiGet.mockResolvedValue({
      summary: { position_count: 1, total_cost_basis: 1800 },
      positions: [{ id: 'pos-1', ticker: 'AAPL', quantity: 10, average_cost: 180, latest_signal: 'Hold' }],
    });
  });

  it('loads positions and deletes one row', async () => {
    const wrapper = mount(PortfolioPositionsPage, {
      global: {
        stubs: {
          Button: { props: ['label', 'disabled'], emits: ['click'], template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}<slot /></button>' },
          Message: { template: '<div><slot /></div>' },
          MetricGrid: { props: ['items'], template: '<div>{{ items.length }}</div>' },
          PageHeader: { template: '<div><slot name="actions" /></div>' },
          PortfolioSubnav: { template: '<nav />' },
          PositionDialog: { props: ['visible'], emits: ['update:visible', 'saved'], template: '<div />' },
          Tag: { props: ['value'], template: '<span>{{ value }}</span>' },
        },
      },
    });

    await flushPromises();
    expect(apiGet).toHaveBeenCalledWith('/api/portfolio', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(wrapper.text()).toContain('AAPL');

    await wrapper.get('[data-testid="position-delete-pos-1"]').trigger('click');
    expect(apiDelete).toHaveBeenCalledWith('/api/portfolio/positions/pos-1', { tenantId: 'tenant-a', apiToken: 'token-a' });
  });
});
