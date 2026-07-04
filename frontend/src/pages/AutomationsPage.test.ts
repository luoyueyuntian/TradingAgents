import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import AutomationsPage from './AutomationsPage.vue';

const { apiGet, apiPost, apiPatch, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

const buildOneTimeTaskPayload = vi.hoisted(() => vi.fn((form) => ({
  builtFromName: form.name,
  manualStocks: form.manualStocks,
  selectedGroupIds: form.selectedGroupIds,
  includeWatchlist: form.includeWatchlist,
})));

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

vi.mock('./oneTimeTaskPayload', () => ({
  buildOneTimeTaskPayload,
}));

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type', 'icon', 'severity', 'outlined', 'text'],
  emits: ['click'],
  template: `
    <button
      :type="type || 'button'"
      :disabled="disabled"
      @click="$emit('click', $event)"
    >
      {{ label }}<slot />
    </button>
  `,
};

const InputTextStub = {
  props: ['modelValue', 'type', 'placeholder', 'disabled'],
  emits: ['update:modelValue'],
  template: `
    <input
      :type="type || 'text'"
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="$emit('update:modelValue', $event.target.value)"
    >
  `,
};

const TextareaStub = {
  props: ['modelValue', 'rows', 'disabled', 'placeholder'],
  emits: ['update:modelValue'],
  template: `
    <textarea
      :value="modelValue"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="$emit('update:modelValue', $event.target.value)"
    />
  `,
};

const SelectStub = {
  props: ['modelValue', 'options', 'optionLabel', 'optionValue', 'disabled'],
  emits: ['update:modelValue', 'change'],
  methods: {
    optionValueFor(option: Record<string, unknown>) {
      if (!option) {
        return '';
      }
      if (this.optionValue && option[this.optionValue] !== undefined) {
        return String(option[this.optionValue]);
      }
      return String(option.value ?? option);
    },
    optionLabelFor(option: Record<string, unknown>) {
      if (!option) {
        return '';
      }
      if (this.optionLabel && option[this.optionLabel] !== undefined) {
        return String(option[this.optionLabel]);
      }
      return String(option.label ?? option.value ?? option);
    },
  },
  template: `
    <select
      :value="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.value); $emit('change', { value: $event.target.value })"
    >
      <option
        v-for="option in options || []"
        :key="optionValueFor(option)"
        :value="optionValueFor(option)"
      >
        {{ optionLabelFor(option) }}
      </option>
    </select>
  `,
};

function mountPage() {
  return mount(AutomationsPage, {
    global: {
      stubs: {
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        InputText: InputTextStub,
        Message: { template: '<div><slot /></div>' },
        PageHeader: { template: '<div><slot name="actions" /></div>' },
        Select: SelectStub,
        Tag: { props: ['value'], template: '<span>{{ value }}</span>' },
        Textarea: TextareaStub,
      },
    },
  });
}

describe('AutomationsPage', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    apiPatch.mockReset();
    apiDelete.mockReset();
    buildOneTimeTaskPayload.mockClear();

    apiGet.mockImplementation((path: string) => {
      if (path === '/api/providers') {
        return Promise.resolve([
          {
            provider: 'openai',
            display_name: 'OpenAI',
            quick_models: [{ label: 'GPT 5.4 Mini', value: 'gpt-5.4-mini' }],
            deep_models: [{ label: 'GPT 5.5', value: 'gpt-5.5' }],
          },
        ]);
      }
      if (path === '/api/settings') {
        return Promise.resolve({
          llm: {
            provider: 'openai',
            quick_think_model: 'gpt-5.4-mini',
            deep_think_model: 'gpt-5.5',
          },
          analysis: {
            research_depth: 3,
            output_language: 'English',
            market_profile: 'default',
            max_risk_discuss_rounds: 2,
            max_recur_limit: 100,
            checkpoint_enabled: false,
            benchmark_ticker: 'QQQ',
          },
        });
      }
      if (path === '/api/automations') {
        return Promise.resolve([]);
      }
      if (path === '/api/one-time-tasks') {
        return Promise.resolve({
          items: [
            {
              id: 'task-1',
              name: 'Night basket',
              status: 'scheduled',
              scheduled_for: '2026-07-10 21:30',
              analysis_date: '2026-07-11',
              selection_snapshot: {
                resolved_tickers: ['AAPL', 'NVDA', 'MSFT'],
              },
            },
          ],
        });
      }
      if (path === '/api/stock-groups') {
        return Promise.resolve([
          { id: 'group-1', name: 'AI Leaders', tickers: ['NVDA', 'MSFT'] },
          { id: 'group-2', name: 'China Internet', tickers: ['0700.HK'] },
        ]);
      }
      if (path === '/api/watchlist') {
        return Promise.resolve([
          { ticker: 'MSFT' },
          { ticker: 'TSLA' },
        ]);
      }
      if (path.startsWith('/api/stocks?market=us')) {
        return Promise.resolve([
          { market: 'us', symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' },
          { market: 'us', symbol: 'NVDA', name: 'NVIDIA', exchange: 'NASDAQ' },
        ]);
      }
      if (path.startsWith('/api/stocks?market=hk')) {
        return Promise.resolve([
          { market: 'hk', symbol: '0700.HK', name: 'Tencent', exchange: 'HKEX' },
        ]);
      }
      return Promise.resolve([]);
    });
  });

  it('loads one-time task sections and existing task rows alongside recurring automations', async () => {
    const wrapper = mountPage();
    await flushPromises();

    expect(apiGet).toHaveBeenCalledWith('/api/automations', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(apiGet).toHaveBeenCalledWith('/api/one-time-tasks', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(apiGet).toHaveBeenCalledWith('/api/stock-groups', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(apiGet).toHaveBeenCalledWith('/api/watchlist', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(wrapper.text()).toContain('One-Time Tasks');
    expect(wrapper.text()).toContain('Night basket');
    expect(wrapper.text()).toContain('AAPL');
    expect(wrapper.text()).toContain('Scheduled');
    expect(wrapper.find('[data-testid="one-time-task-builder"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="one-time-task-list"]').exists()).toBe(true);
  });

  it('keeps manual picks when switching markets and posts the builder payload for one-time tasks', async () => {
    apiPost.mockResolvedValue({ id: 'task-2' });

    const wrapper = mountPage();
    await flushPromises();

    const sections = wrapper.findAll('[data-testid^="one-time-section-"]');
    expect(sections).toHaveLength(5);
    expect(sections[0]?.attributes('data-testid')).toBe('one-time-section-basics');
    expect(sections[1]?.attributes('data-testid')).toBe('one-time-section-manual-stocks');
    expect(sections[2]?.attributes('data-testid')).toBe('one-time-section-groups-watchlist');
    expect(sections[3]?.attributes('data-testid')).toBe('one-time-section-resolved-universe');
    expect(sections[4]?.attributes('data-testid')).toBe('one-time-section-save');

    await wrapper.get('[data-testid="one-time-name"]').setValue('Night basket');
    await wrapper.get('[data-testid="one-time-scheduled-for"]').setValue('2026-07-10 21:30');
    await wrapper.get('[data-testid="one-time-analysis-date"]').setValue('2026-07-11');

    await wrapper.get('[data-testid="manual-stock-market"]').setValue('us');
    await flushPromises();
    await wrapper.get('[data-testid="manual-stock-option"]').setValue('AAPL');
    await wrapper.get('[data-testid="manual-stock-add"]').trigger('click');

    await wrapper.get('[data-testid="manual-stock-market"]').setValue('hk');
    await flushPromises();
    await wrapper.get('[data-testid="manual-stock-option"]').setValue('0700.HK');
    await wrapper.get('[data-testid="manual-stock-add"]').trigger('click');

    const manualSymbols = wrapper.findAll('[data-testid="manual-stock-symbol"]').map((node) => node.text());
    expect(manualSymbols).toEqual(['AAPL', '0700.HK']);

    await wrapper.get('[data-testid="one-time-group-group-1"]').setValue(true);
    await wrapper.get('[data-testid="one-time-include-watchlist"]').setValue(true);
    await flushPromises();

    expect(wrapper.find('[data-testid="resolved-ticker-AAPL"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="resolved-ticker-0700.HK"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="resolved-ticker-NVDA"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="resolved-ticker-MSFT"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="resolved-ticker-TSLA"]').exists()).toBe(true);

    await wrapper.get('[data-testid="one-time-save"]').trigger('click');
    await flushPromises();

    expect(buildOneTimeTaskPayload).toHaveBeenCalledTimes(1);
    expect(buildOneTimeTaskPayload.mock.calls[0]?.[0]).toEqual(expect.objectContaining({
      name: 'Night basket',
      scheduledFor: '2026-07-10 21:30',
      analysisDate: '2026-07-11',
      selectedGroupIds: ['group-1'],
      includeWatchlist: true,
      manualStocks: [
        expect.objectContaining({ market: 'us', symbol: 'AAPL' }),
        expect.objectContaining({ market: 'hk', symbol: '0700.HK' }),
      ],
    }));
    expect(apiPost).toHaveBeenCalledWith('/api/one-time-tasks', {
      builtFromName: 'Night basket',
      manualStocks: [
        expect.objectContaining({ market: 'us', symbol: 'AAPL' }),
        expect.objectContaining({ market: 'hk', symbol: '0700.HK' }),
      ],
      selectedGroupIds: ['group-1'],
      includeWatchlist: true,
    }, { tenantId: 'tenant-a', apiToken: 'token-a' });
  });
});
