import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { setLocale } from '../i18n';
import AutomationsPage from './AutomationsPage.vue';

const { apiGet, apiPost, apiPatch, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
  apiDelete: vi.fn(),
}));

const buildOneTimeTaskPayload = vi.hoisted(() => vi.fn((form) => ({
  id: form.id,
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

function optionValueFor(
  option: Record<string, unknown>,
  optionValue?: string,
) {
  if (!option) {
    return '';
  }
  if (optionValue && option[optionValue] !== undefined) {
    return String(option[optionValue]);
  }
  return String(option.value ?? option);
}

function optionLabelFor(
  option: Record<string, unknown>,
  optionLabel?: string,
) {
  if (!option) {
    return '';
  }
  if (optionLabel && option[optionLabel] !== undefined) {
    return String(option[optionLabel]);
  }
  return String(option.label ?? option.value ?? option);
}

function selectedValues(event: Event) {
  return Array.from((event.target as HTMLSelectElement).selectedOptions).map((option) => option.value);
}

const SelectStub = {
  props: ['modelValue', 'options', 'optionLabel', 'optionValue', 'disabled'],
  emits: ['update:modelValue', 'change'],
  computed: {
    optionValueForFn() {
      return optionValueFor;
    },
    optionLabelForFn() {
      return optionLabelFor;
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
        :key="optionValueForFn(option, optionValue)"
        :value="optionValueForFn(option, optionValue)"
      >
        {{ optionLabelForFn(option, optionLabel) }}
      </option>
    </select>
  `,
};

const MultiSelectStub = {
  props: ['modelValue', 'options', 'optionLabel', 'optionValue', 'disabled'],
  emits: ['update:modelValue', 'change'],
  computed: {
    optionValueForFn() {
      return optionValueFor;
    },
    optionLabelForFn() {
      return optionLabelFor;
    },
    selectedValuesFn() {
      return selectedValues;
    },
  },
  template: `
    <select
      multiple
      :value="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', selectedValuesFn($event)); $emit('change', { value: selectedValuesFn($event) })"
    >
      <option
        v-for="option in options || []"
        :key="optionValueForFn(option, optionValue)"
        :value="optionValueForFn(option, optionValue)"
      >
        {{ optionLabelForFn(option, optionLabel) }}
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
        MultiSelect: MultiSelectStub,
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
    setLocale('en');
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
              manual_stocks: [{ market: 'us', symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' }],
              group_ids: ['group-1'],
              include_watchlist: true,
              selection_snapshot: {
                manual_stocks: [{ market: 'us', symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' }],
                group_snapshots: [{ id: 'group-1', name: 'AI Leaders', tickers: ['NVDA', 'MSFT'] }],
                include_watchlist: true,
                resolved_tickers: ['AAPL', 'NVDA', 'MSFT'],
              },
              analysis_config: {
                analysts: ['market'],
                llm_provider: 'openai',
                quick_think_model: 'saved-quick-model',
                deep_think_model: 'saved-deep-model',
                research_depth: 5,
                output_language: 'Chinese',
              },
            },
            {
              id: 'task-2',
              name: 'Completed basket',
              status: 'completed',
              scheduled_for: '2026-07-09 21:30',
              analysis_date: '2026-07-10',
              run_ids: ['run-7', 'run-8'],
              selection_snapshot: {
                manual_stocks: [],
                group_snapshots: [],
                include_watchlist: false,
                resolved_tickers: ['NVDA', 'MSFT'],
              },
            },
            {
              id: 'task-3',
              name: 'Queued basket',
              status: 'queued',
              scheduled_for: '2026-07-11 09:00',
              analysis_date: '2026-07-11',
              run_ids: ['run-9'],
              selection_snapshot: {
                manual_stocks: [],
                group_snapshots: [],
                include_watchlist: false,
                resolved_tickers: ['AAPL'],
              },
            },
            {
              id: 'task-4',
              name: 'Running basket',
              status: 'running',
              scheduled_for: '2026-07-11 09:01',
              analysis_date: '2026-07-11',
              run_ids: ['run-10'],
              selection_snapshot: {
                manual_stocks: [],
                group_snapshots: [],
                include_watchlist: false,
                resolved_tickers: ['NVDA'],
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
    expect(wrapper.text()).toContain('Queued');
    expect(wrapper.text()).toContain('Running');
    expect(wrapper.text()).toContain('Manual 1');
    expect(wrapper.text()).toContain('Groups 1');
    expect(wrapper.text()).toContain('Watchlist included');
    expect(wrapper.text()).toContain('3 stocks');
    expect(wrapper.find('[data-testid="one-time-task-builder"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="one-time-task-list"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="edit-one-time-task-task-1"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="cancel-one-time-task-task-1"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="completed-task-run-run-7"]').attributes('href')).toBe('/runs/run-7');
  });

  it('preserves source composition while only normalizing the affected source on resolved ticker removal', async () => {
    apiPost.mockResolvedValue({ id: 'task-2' });
    apiPatch.mockResolvedValue({ id: 'task-1' });

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
    await wrapper.get('[data-testid="manual-stock-multi"]').setValue(['AAPL']);

    await wrapper.get('[data-testid="manual-stock-market"]').setValue('hk');
    await flushPromises();
    await wrapper.get('[data-testid="manual-stock-multi"]').setValue(['0700.HK']);

    const manualSymbols = wrapper.findAll('[data-testid="manual-stock-symbol"]').map((node) => node.text());
    expect(manualSymbols).toEqual(['AAPL', '0700.HK']);

    await wrapper.get('[data-testid="one-time-group-group-1"]').setValue(true);
    await wrapper.get('[data-testid="one-time-include-watchlist"]').setValue(true);
    await flushPromises();

    expect(wrapper.find('[data-testid="selected-group-chip-group-1"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('5 stocks');
    expect(wrapper.find('[data-testid="resolved-ticker-AAPL"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="resolved-ticker-0700.HK"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="resolved-ticker-NVDA"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="resolved-ticker-MSFT"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="resolved-ticker-TSLA"]').exists()).toBe(true);
    await wrapper.get('[data-testid="remove-resolved-ticker-TSLA"]').trigger('click');
    await flushPromises();
    expect(wrapper.find('[data-testid="resolved-ticker-TSLA"]').exists()).toBe(false);
    expect(wrapper.text()).toContain('4 stocks');
    expect(wrapper.find('[data-testid="selected-group-chip-group-1"]').exists()).toBe(true);
    expect((wrapper.get('[data-testid="one-time-include-watchlist"]').element as HTMLInputElement).checked).toBe(false);

    await wrapper.get('[data-testid="remove-resolved-ticker-NVDA"]').trigger('click');
    await flushPromises();
    expect(wrapper.find('[data-testid="resolved-ticker-NVDA"]').exists()).toBe(false);
    expect(wrapper.find('[data-testid="resolved-ticker-MSFT"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('3 stocks');
    expect(wrapper.find('[data-testid="selected-group-chip-group-1"]').exists()).toBe(false);
    expect(wrapper.findAll('[data-testid="manual-stock-symbol"]').map((node) => node.text())).toEqual(['AAPL', '0700.HK', 'MSFT']);

    await wrapper.get('[data-testid="one-time-save"]').trigger('click');
    await flushPromises();

    expect(buildOneTimeTaskPayload).toHaveBeenCalledTimes(1);
    expect(buildOneTimeTaskPayload.mock.calls[0]?.[0]).toEqual(expect.objectContaining({
      name: 'Night basket',
      scheduledFor: '2026-07-10 21:30',
      analysisDate: '2026-07-11',
      selectedGroupIds: [],
      includeWatchlist: false,
      manualStocks: [
        expect.objectContaining({ market: 'us', symbol: 'AAPL' }),
        expect.objectContaining({ symbol: '0700.HK' }),
        expect.objectContaining({ symbol: 'MSFT' }),
      ],
    }));
    expect(apiPost).toHaveBeenCalledWith('/api/one-time-tasks', {
      builtFromName: 'Night basket',
      manualStocks: [
        expect.objectContaining({ market: 'us', symbol: 'AAPL' }),
        expect.objectContaining({ symbol: '0700.HK' }),
        expect.objectContaining({ symbol: 'MSFT' }),
      ],
      selectedGroupIds: [],
      includeWatchlist: false,
    }, { tenantId: 'tenant-a', apiToken: 'token-a' });

    await wrapper.get('[data-testid="edit-one-time-task-task-1"]').trigger('click');
    await flushPromises();
    expect((wrapper.get('[data-testid="one-time-name"]').element as HTMLInputElement).value).toBe('Night basket');
    expect((wrapper.get('[data-testid="one-time-scheduled-for"]').element as HTMLInputElement).value).toBe('2026-07-10 21:30');
    expect((wrapper.get('[data-testid="one-time-analysis-date"]').element as HTMLInputElement).value).toBe('2026-07-11');
    expect((wrapper.get('[data-testid="one-time-quick-model"]').element as HTMLInputElement).value).toBe('saved-quick-model');
    expect((wrapper.get('[data-testid="one-time-deep-model"]').element as HTMLInputElement).value).toBe('saved-deep-model');
    expect((wrapper.get('[data-testid="one-time-research-depth"]').element as HTMLSelectElement).value).toBe('5');
    expect((wrapper.get('[data-testid="one-time-output-language"]').element as HTMLSelectElement).value).toBe('Chinese');
    expect(wrapper.find('[data-testid="resolved-ticker-AAPL"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="resolved-ticker-NVDA"]').exists()).toBe(true);
    expect(wrapper.find('[data-testid="resolved-ticker-MSFT"]').exists()).toBe(true);
    expect(wrapper.findAll('[data-testid="manual-stock-symbol"]').map((node) => node.text())).toEqual(['AAPL']);
    expect(wrapper.find('[data-testid="selected-group-chip-group-1"]').exists()).toBe(true);
    expect((wrapper.get('[data-testid="one-time-include-watchlist"]').element as HTMLInputElement).checked).toBe(true);

    await wrapper.get('[data-testid="remove-resolved-ticker-MSFT"]').trigger('click');
    await flushPromises();
    await wrapper.get('[data-testid="one-time-name"]').setValue('Night basket updated');
    await wrapper.get('[data-testid="one-time-save"]').trigger('click');
    await flushPromises();

    expect(apiPatch).toHaveBeenCalledWith('/api/one-time-tasks/task-1', {
      id: 'task-1',
      builtFromName: 'Night basket updated',
      manualStocks: [
        expect.objectContaining({ symbol: 'AAPL' }),
        expect.objectContaining({ symbol: 'NVDA' }),
        expect.objectContaining({ symbol: 'TSLA' }),
      ],
      selectedGroupIds: [],
      includeWatchlist: false,
    }, { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect((wrapper.get('[data-testid="one-time-name"]').element as HTMLInputElement).value).toBe('');
    expect((wrapper.get('[data-testid="one-time-quick-model"]').element as HTMLInputElement).value).toBe('gpt-5.4-mini');
    expect((wrapper.get('[data-testid="one-time-deep-model"]').element as HTMLInputElement).value).toBe('gpt-5.5');
    expect((wrapper.get('[data-testid="one-time-research-depth"]').element as HTMLSelectElement).value).toBe('3');
    expect((wrapper.get('[data-testid="one-time-output-language"]').element as HTMLSelectElement).value).toBe('English');

    await wrapper.get('[data-testid="edit-one-time-task-task-1"]').trigger('click');
    await flushPromises();
    await wrapper.get('[data-testid="one-time-quick-model"]').setValue('temporary-model');
    await wrapper.get('[data-testid="cancel-one-time-task-task-1"]').trigger('click');
    await flushPromises();
    expect(apiPost).toHaveBeenCalledWith('/api/one-time-tasks/task-1/cancel', {}, { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect((wrapper.get('[data-testid="one-time-name"]').element as HTMLInputElement).value).toBe('');
    expect((wrapper.get('[data-testid="one-time-quick-model"]').element as HTMLInputElement).value).toBe('gpt-5.4-mini');
    expect((wrapper.get('[data-testid="one-time-deep-model"]').element as HTMLInputElement).value).toBe('gpt-5.5');
    expect((wrapper.get('[data-testid="one-time-research-depth"]').element as HTMLSelectElement).value).toBe('3');
    expect((wrapper.get('[data-testid="one-time-output-language"]').element as HTMLSelectElement).value).toBe('English');
    expect((wrapper.get('[data-testid="one-time-include-watchlist"]').element as HTMLInputElement).checked).toBe(false);
  });
});
