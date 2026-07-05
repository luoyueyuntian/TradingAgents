import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PortfolioWatchlistPage from './PortfolioWatchlistPage.vue';

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

describe('PortfolioWatchlistPage', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiDelete.mockReset();
    apiGet.mockResolvedValue([{ ticker: 'NVDA', company_name: 'NVIDIA Corporation', latest_signal: 'Buy', latest_status: 'completed' }]);
  });

  it('loads watchlist rows and deletes a ticker', async () => {
    const wrapper = mount(PortfolioWatchlistPage, {
      global: {
        stubs: {
          Button: { props: ['label', 'disabled'], emits: ['click'], template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}<slot /></button>' },
          Message: { template: '<div><slot /></div>' },
          MetricGrid: { props: ['items'], template: '<div>{{ items.length }}</div>' },
          PageHeader: { template: '<div><slot name="actions" /></div>' },
          PortfolioSubnav: { template: '<nav />' },
          Tag: { props: ['value'], template: '<span>{{ value }}</span>' },
          WatchlistCreateDialog: { props: ['visible'], emits: ['update:visible', 'saved'], template: '<div />' },
        },
      },
    });

    await flushPromises();
    expect(apiGet).toHaveBeenCalledWith('/api/watchlist', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(wrapper.text()).toContain('NVDA');
    expect(wrapper.text()).toContain('NVIDIA Corporation');

    await wrapper.get('[data-testid="watchlist-delete-NVDA"]').trigger('click');
    expect(apiDelete).toHaveBeenCalledWith('/api/watchlist/NVDA', { tenantId: 'tenant-a', apiToken: 'token-a' });
  });
});
