import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PortfolioPage from './PortfolioPage.vue';

const { apiGet, apiPost, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiDelete: vi.fn(),
}));

vi.mock('../services/api', () => ({
  apiGet,
  apiPost,
  apiDelete,
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
        Select: SelectStub,
        Tag: { props: ['value'], template: '<span>{{ value }}</span>' },
      },
    },
  });
}

describe('PortfolioPage', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    apiDelete.mockReset();

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

  it('loads stock groups and creates a new group from the portfolio page', async () => {
    apiPost.mockResolvedValue({ id: 'group-3', name: 'Semis', tickers: ['AMD', 'AVGO'] });

    const wrapper = mountPage();
    await flushPromises();

    expect(apiGet).toHaveBeenCalledWith('/api/stock-groups', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(wrapper.text()).toContain('Stock Groups');
    expect(wrapper.text()).toContain('AI Leaders');
    expect(wrapper.text()).toContain('NVDA, MSFT');
    expect(wrapper.text()).toContain('China Internet');
    expect(wrapper.find('[data-testid="stock-group-delete-group-1"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="stock-group-delete-group-2"]').exists()).toBe(true);

    await wrapper.get('[data-testid="stock-group-name"]').setValue('Semis');
    await wrapper.get('[data-testid="stock-group-tickers"]').setValue('amd, avgo');
    await wrapper.get('[data-testid="stock-group-add"]').trigger('click');
    await flushPromises();

    expect(apiPost).toHaveBeenCalledWith(
      '/api/stock-groups',
      { name: 'Semis', tickers: ['AMD', 'AVGO'] },
      { tenantId: 'tenant-a', apiToken: 'token-a' },
    );
    expect(apiGet).toHaveBeenCalledTimes(6);
  });
});
