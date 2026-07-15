import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import AnalyzePage from './AnalyzePage.vue';

const { apiGet, apiPost } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiPost: vi.fn(),
}));

vi.mock('../services/api', () => ({
  apiGet,
  apiPost,
}));

const push = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push,
  }),
}));

vi.mock('../stores/session', () => ({
  useSession: () => ({
    apiContext: { value: { tenantId: 'tenant-a' } },
    canWrite: { value: true },
  }),
}));

const SelectStub = {
  name: 'SelectStub',
  props: ['modelValue', 'options', 'optionLabel', 'optionValue', 'disabled'],
  emits: ['update:modelValue', 'change'],
  template: `
    <select
      v-bind="$attrs"
      :value="modelValue"
      :disabled="disabled"
      @change="$emit('update:modelValue', $event.target.value); $emit('change', $event)"
    >
      <option
        v-for="option in options"
        :key="option[optionValue || 'value']"
        :value="option[optionValue || 'value']"
      >
        {{ option[optionLabel || 'label'] }}
      </option>
    </select>
  `,
};

const DatePickerStub = {
  name: 'DatePickerStub',
  props: ['manualInput', 'modelValue', 'dateFormat', 'showIcon', 'iconDisplay', 'fluid', 'inputClass'],
  emits: ['update:modelValue'],
  methods: {
    formatValue(value: Date | null) {
      if (!(value instanceof Date) || Number.isNaN(value.getTime())) {
        return '';
      }
      const year = value.getFullYear();
      const month = String(value.getMonth() + 1).padStart(2, '0');
      const day = String(value.getDate()).padStart(2, '0');
      return `${year}-${month}-${day}`;
    },
    handleInput(event: Event) {
      const value = (event.target as HTMLInputElement).value;
      this.$emit('update:modelValue', value ? new Date(`${value}T00:00:00`) : null);
    },
  },
  template: `
    <input
      data-testid="analysis-date-input"
      :value="formatValue(modelValue)"
      @input="handleInput"
    >
  `,
};

const AutoCompleteStub = {
  emits: ['update:modelValue', 'complete', 'clear'],
  template: `
    <div>
      <button
        data-testid="select-stock"
        type="button"
        @click="$emit('update:modelValue', { symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ', market: 'us', label: 'AAPL · Apple Inc. · NASDAQ' })"
      >
        select
      </button>
    </div>
  `,
};

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type'],
  emits: ['click'],
  template: `
    <button
      v-bind="$attrs"
      :type="type || 'button'"
      :disabled="disabled"
      @click="$emit('click', $event)"
    >
      {{ label }}<slot />
    </button>
  `,
};

function resolveBootPayload(path: string) {
  switch (path) {
    case '/api/providers':
      return Promise.resolve([{ provider: 'openai', display_name: 'OpenAI', quick_models: [], deep_models: [] }]);
    case '/api/stocks/markets':
      return Promise.resolve([{ value: 'us', label: 'US' }]);
    case '/api/settings':
      return Promise.resolve({ llm: {}, analysis: {} });
    default:
      if (path.startsWith('/api/runs/ticker-history')) {
        return Promise.resolve({
          ticker: 'AAPL',
          company_name: 'Apple Inc.',
          has_active_run: false,
          active_run_id: null,
          active_run_status: null,
          page: 1,
          page_size: 10,
          total_count: 0,
          items: [],
        });
      }
      if (path.startsWith('/api/stocks')) {
        return Promise.resolve([{ symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ', market: 'us' }]);
      }
      throw new Error(`Unexpected boot path: ${path}`);
  }
}

async function mountPage() {
  const wrapper = mount(AnalyzePage, {
    global: {
      stubs: {
        AutoComplete: AutoCompleteStub,
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        DatePicker: DatePickerStub,
        InputText: { template: '<input />' },
        Message: { template: '<div><slot /></div>' },
        MetricGrid: { template: '<div />' },
        PageHeader: { template: '<div><slot name="actions" /></div>' },
        ReportMarkdown: { template: '<div />' },
        RunHistoryConfirmDialog: { template: '<div />' },
        Select: SelectStub,
        Tag: { template: '<span />' },
      },
    },
  });

  await flushPromises();
  return wrapper;
}

function findButtonByText(wrapper: VueWrapper<InstanceType<typeof AnalyzePage>>, label: string) {
  const button = wrapper.findAll('button').find((item) => item.text().trim() === label);
  if (!button) {
    throw new Error(`Button "${label}" not found`);
  }
  return button;
}

function findMarketProfileSelect(wrapper: VueWrapper<InstanceType<typeof AnalyzePage>>) {
  const component = wrapper.findAllComponents({ name: 'SelectStub' }).find((item) => {
    const options = item.props('options') as Array<{ value: string }> | undefined;
    return Array.isArray(options) && options.some((option) => option.value === 'default') && options.some((option) => option.value === 'cn_a');
  });
  if (!component) {
    throw new Error('Market profile select not found');
  }
  return component.get('select');
}

describe('AnalyzePage editability', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiPost.mockReset();
    push.mockReset();
    apiGet.mockImplementation((path: string) => resolveBootPayload(path));
  });

  it('keeps market profile editable for one-off runs', async () => {
    const wrapper = await mountPage();
    const marketProfileSelect = wrapper.findAllComponents({ name: 'SelectStub' }).find((component) => {
      const options = component.props('options') as Array<{ value: string }> | undefined;
      return Array.isArray(options) && options.some((option) => option.value === 'default') && options.some((option) => option.value === 'cn_a');
    });

    expect(marketProfileSelect).toBeDefined();
    expect(Boolean(marketProfileSelect?.props('disabled'))).toBe(false);
  });

  it('allows manual analysis-date entry in addition to the picker', async () => {
    const wrapper = await mountPage();
    const datePicker = wrapper.findComponent({ name: 'DatePickerStub' });

    expect(datePicker.exists()).toBe(true);
    expect(datePicker.props('manualInput')).toBe(true);
  });

  it('submits a one-off market profile override in the run request payload', async () => {
    apiPost.mockResolvedValueOnce({ run_id: 'run-1', status: 'queued', ticker: 'AAPL', date: '2026-07-15' });

    const wrapper = await mountPage();
    await wrapper.get('[data-testid="select-stock"]').trigger('click');
    await flushPromises();
    await findMarketProfileSelect(wrapper).setValue('cn_a');
    await findButtonByText(wrapper, '开始分析').trigger('click');
    await flushPromises();

    expect(apiPost).toHaveBeenCalledWith(
      '/api/runs',
      expect.objectContaining({
        ticker: 'AAPL',
        market_profile: 'cn_a',
      }),
      expect.anything(),
    );
  });

  it('submits a manually entered analysis date in the run request payload', async () => {
    apiPost.mockResolvedValueOnce({ run_id: 'run-1', status: 'queued', ticker: 'AAPL', date: '2026-07-15' });

    const wrapper = await mountPage();
    await wrapper.get('[data-testid="select-stock"]').trigger('click');
    await flushPromises();
    await wrapper.get('[data-testid="analysis-date-input"]').setValue('2026-07-04');
    await findButtonByText(wrapper, '开始分析').trigger('click');
    await flushPromises();

    expect(apiPost).toHaveBeenCalledWith(
      '/api/runs',
      expect.objectContaining({
        ticker: 'AAPL',
        date: '2026-07-04',
      }),
      expect.anything(),
    );
  });
});
