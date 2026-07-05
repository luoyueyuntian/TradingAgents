import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PortfolioPage from './PortfolioPage.vue';

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock('../services/api', () => ({
  apiGet,
}));

vi.mock('../stores/session', () => ({
  useSession: () => ({
    apiContext: { value: { tenantId: 'tenant-a', apiToken: 'token-a' } },
    canWrite: { value: true },
  }),
}));

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type', 'icon', 'severity', 'outlined', 'text', 'ariaLabel'],
  emits: ['click'],
  template: `
    <button
      :type="type || 'button'"
      :disabled="disabled"
      :aria-label="ariaLabel"
      @click="$emit('click', $event)"
    >
      {{ label }}<slot />
    </button>
  `,
};

const InputTextStub = {
  props: ['modelValue', 'type', 'placeholder', 'disabled'],
  emits: ['update:modelValue', 'input'],
  template: `
    <input
      :type="type || 'text'"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="$emit('update:modelValue', $event.target.value); $emit('input', $event)"
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
      @change="$emit('update:modelValue', $event.target.value); $emit('change', { value: $event.target.value })"
    >
      <option
        v-for="option in options || []"
        :key="String(optionValue ? option[optionValue] : option.value ?? option)"
        :value="String(optionValue ? option[optionValue] : option.value ?? option)"
      >
        {{ String(optionLabel ? option[optionLabel] : option.label ?? option.value ?? option) }}
      </option>
    </select>
  `,
};

function mountPage() {
  return mount(PortfolioPage, {
    global: {
      stubs: {
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        Column: { template: '<div><slot /></div>' },
        DataTable: { template: '<div><slot /></div>' },
        InputText: InputTextStub,
        Message: { template: '<div><slot /></div>' },
        MetricGrid: { props: ['items'], template: '<div data-testid="metric-grid-stub">{{ items.length }}</div>' },
        PageHeader: { template: '<div><slot name="actions" /></div>' },
        PortfolioSubnav: { template: '<nav />' },
        RouterLink: { props: ['to'], template: '<a :data-to="to"><slot /></a>' },
        Select: SelectStub,
        Tag: { props: ['value'], template: '<span>{{ value }}</span>' },
      },
    },
  });
}

describe('PortfolioPage', () => {
  beforeEach(() => {
    apiGet.mockReset();

    apiGet.mockImplementation((path: string) => {
      if (path === '/api/watchlist') {
        return Promise.resolve([{ ticker: 'MSFT', latest_signal: 'buy' }]);
      }
      if (path === '/api/portfolio') {
        return Promise.resolve({ positions: [{ id: 'pos-1', ticker: 'AAPL', quantity: 10, average_cost: 180 }] });
      }
      if (path === '/api/alerts') {
        return Promise.resolve({ rules: [{ id: 'alert-1', ticker: 'NVDA', field: 'signal', value: 'buy' }] });
      }
      if (path.startsWith('/api/screener?')) {
        return Promise.resolve({ rows: [{ ticker: 'TSLA', latest_status: 'ready', latest_signal: 'hold', run_count: 2 }] });
      }
      if (path === '/api/stock-groups') {
        return Promise.resolve([
          { id: 'group-1', name: 'AI Leaders', tickers: ['NVDA', 'MSFT'] },
          { id: 'group-2', name: 'China Internet', tickers: ['BABA', '0700.HK'] },
        ]);
      }
      return Promise.resolve([]);
    });
  });

  it('loads the portfolio home summary and links to the dedicated asset pages', async () => {
    const wrapper = mountPage();
    await flushPromises();

    expect(apiGet).toHaveBeenCalledWith('/api/watchlist', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(apiGet).toHaveBeenCalledWith('/api/portfolio', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(apiGet).toHaveBeenCalledWith('/api/alerts', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(apiGet).toHaveBeenCalledWith('/api/stock-groups', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(wrapper.find('[data-to="/portfolio/watchlist"]').exists()).toBe(true);
    expect(wrapper.find('[data-to="/portfolio/positions"]').exists()).toBe(true);
    expect(wrapper.find('[data-to="/portfolio/stock-groups"]').exists()).toBe(true);
    expect(wrapper.find('[data-to="/portfolio/alerts"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid^="stock-group-delete-"]').exists()).toBe(false);
  });
});
