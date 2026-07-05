import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PortfolioStockPicker from './PortfolioStockPicker.vue';

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock('../../services/api', () => ({
  apiGet,
}));

vi.mock('../../stores/session', () => ({
  useSession: () => ({
    apiContext: { value: { tenantId: 'tenant-a', apiToken: 'token-a' } },
  }),
}));

describe('PortfolioStockPicker', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiGet.mockImplementation((path: string) => {
      if (path === '/api/stocks/markets') {
        return Promise.resolve([
          { value: 'us', label: 'US' },
          { value: 'hk', label: 'HK' },
        ]);
      }
      if (path.startsWith('/api/stocks?')) {
        return Promise.resolve([
          { market: 'us', symbol: 'NVDA', name: 'NVIDIA', exchange: 'NASDAQ' },
        ]);
      }
      return Promise.resolve([]);
    });
  });

  it('loads markets, searches stocks, and emits the selected option', async () => {
    const wrapper = mount(PortfolioStockPicker, {
      global: {
        stubs: {
          AutoComplete: {
            props: ['modelValue', 'suggestions'],
            emits: ['update:modelValue', 'complete', 'clear'],
            template: '<button data-testid="autocomplete" @click="$emit(\'complete\', { query: \'nvi\' })">{{ suggestions.length }}</button>',
          },
          Select: {
            props: ['modelValue', 'options'],
            emits: ['update:modelValue', 'change'],
            template: '<button data-testid="market-select" @click="$emit(\'update:modelValue\', \'hk\'); $emit(\'change\', { value: \'hk\' })">{{ modelValue }}</button>',
          },
        },
      },
    });

    await flushPromises();
    await wrapper.get('[data-testid="autocomplete"]').trigger('click');
    await flushPromises();

    expect(apiGet).toHaveBeenCalledWith('/api/stocks/markets', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(apiGet.mock.calls.some(([path]) => String(path).startsWith('/api/stocks?market=us'))).toBe(true);
  });
});
