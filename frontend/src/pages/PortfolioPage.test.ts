import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PortfolioPage from './PortfolioPage.vue';

const { apiGet, apiPost, apiPatch, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

vi.mock('../services/api', () => ({
  apiGet,
  apiPost,
  apiPatch,
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

let stockGroups: Array<{ id: string; name: string; tickers: string[] }> = [];

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
    apiPatch.mockReset();
    apiDelete.mockReset();

    stockGroups = [
      { id: 'group-1', name: 'AI Leaders', tickers: ['NVDA', 'MSFT'] },
      { id: 'group-2', name: 'China Internet', tickers: ['BABA', '0700.HK'] },
    ];

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
        return Promise.resolve(stockGroups.map((group) => ({
          ...group,
          tickers: [...group.tickers],
        })));
      }
      return Promise.resolve([]);
    });

    apiPost.mockImplementation(async (path: string, body: Record<string, unknown>) => {
      if (path === '/api/stock-groups') {
        const group = {
          id: 'group-3',
          name: String(body.name),
          tickers: body.tickers as string[],
        };
        stockGroups = [...stockGroups, group];
        return Promise.resolve(group);
      }
      return Promise.resolve({});
    });

    apiPatch.mockImplementation(async (path: string, body: Record<string, unknown>) => {
      const groupId = path.split('/').pop();
      stockGroups = stockGroups.map((group) => (
        group.id === groupId
          ? { ...group, name: String(body.name), tickers: body.tickers as string[] }
          : group
      ));
      const group = stockGroups.find((item) => item.id === groupId);
      return Promise.resolve(group ?? {});
    });

    apiDelete.mockImplementation(async (path: string) => {
      const groupId = path.split('/').pop();
      stockGroups = stockGroups.filter((group) => group.id !== groupId);
      return Promise.resolve({});
    });
  });

  it('loads stock groups and supports create, edit, and delete from the portfolio page', async () => {
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
    await wrapper.get('[data-testid="stock-group-save"]').trigger('click');
    await flushPromises();

    expect(apiPost).toHaveBeenCalledWith(
      '/api/stock-groups',
      { name: 'Semis', tickers: ['AMD', 'AVGO'] },
      { tenantId: 'tenant-a', apiToken: 'token-a' },
    );
    expect(wrapper.text()).toContain('Semis');
    expect(wrapper.text()).toContain('AMD, AVGO');

    await wrapper.get('[data-testid="stock-group-edit-group-1"]').trigger('click');
    await wrapper.get('[data-testid="stock-group-name"]').setValue('AI Leaders Core');
    await wrapper.get('[data-testid="stock-group-tickers"]').setValue('nvda, msft, avgo');
    await wrapper.get('[data-testid="stock-group-save"]').trigger('click');
    await flushPromises();

    expect(apiPatch).toHaveBeenCalledWith(
      '/api/stock-groups/group-1',
      { name: 'AI Leaders Core', tickers: ['NVDA', 'MSFT', 'AVGO'] },
      { tenantId: 'tenant-a', apiToken: 'token-a' },
    );
    expect(wrapper.text()).toContain('AI Leaders Core');
    expect(wrapper.text()).toContain('NVDA, MSFT, AVGO');

    await wrapper.get('[data-testid="stock-group-delete-group-2"]').trigger('click');
    await flushPromises();

    expect(apiDelete).toHaveBeenCalledWith('/api/stock-groups/group-2', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(wrapper.text()).not.toContain('China Internet');
  });
});
