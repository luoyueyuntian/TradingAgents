import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

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

const session = {
  apiContext: { value: { tenantId: 'tenant-a' } },
  canWrite: { value: true },
};

vi.mock('../stores/session', () => ({
  useSession: () => session,
}));

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type', 'icon', 'severity', 'outlined'],
  emits: ['click'],
  template: `
    <button v-bind="$attrs" :type="type || 'button'" :disabled="disabled" @click="$emit('click', $event)">
      {{ label }}<slot />
    </button>
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

const SelectStub = {
  props: ['modelValue', 'options', 'optionLabel', 'optionValue', 'disabled'],
  emits: ['update:modelValue', 'change'],
  template: `
    <select v-bind="$attrs" :value="modelValue" :disabled="disabled" @change="$emit('update:modelValue', $event.target.value); $emit('change', $event)">
      <option v-for="option in options" :key="option[optionValue || 'value']" :value="option[optionValue || 'value']">
        {{ option[optionLabel || 'label'] }}
      </option>
    </select>
  `,
};

const DatePickerStub = {
  template: '<div />',
};

const InputTextStub = {
  props: ['modelValue', 'type', 'placeholder'],
  emits: ['update:modelValue'],
  template: '<input v-bind="$attrs" :value="modelValue" :type="type || \'text\'" :placeholder="placeholder">',
};

const RunHistoryConfirmDialogStub = {
  props: ['visible', 'mode', 'historyPage'],
  emits: ['update:visible', 'confirm', 'row-open', 'page-change'],
  template: `
    <div v-if="visible" data-testid="history-dialog">
      <span>{{ mode === 'active' ? '立即查看' : '启动新的分析' }}</span>
      <button data-testid="history-dialog-confirm" type="button" @click="$emit('confirm')">confirm</button>
      <button data-testid="history-dialog-row" type="button" @click="$emit('row-open', historyPage.items[0])">row</button>
    </div>
  `,
};

function resolveAnalyzeBootPayload(path: string) {
  switch (path) {
    case '/api/providers':
      return Promise.resolve([{ provider: 'openai', display_name: 'OpenAI', quick_models: [], deep_models: [] }]);
    case '/api/stocks/markets':
      return Promise.resolve([{ value: 'us', label: 'US' }]);
    case '/api/settings':
      return Promise.resolve({ llm: {}, analysis: {} });
    default:
      if (path.startsWith('/api/stocks')) {
        return Promise.resolve([{ symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ', market: 'us' }]);
      }
      throw new Error(`Unexpected boot path: ${path}`);
  }
}

function sampleRecentHistoryPage(overrides: Record<string, unknown> = {}) {
  return {
    ticker: 'AAPL',
    company_name: 'Apple Inc.',
    has_active_run: false,
    active_run_id: null,
    active_run_status: null,
    page: 1,
    page_size: 10,
    total_count: 1,
    items: [
      {
        run_id: 'run-recent',
        ticker: 'AAPL',
        date: '2026-07-05',
        status: 'completed',
        signal: 'Buy',
        created_at: '2026-07-05T08:30:00+08:00',
      },
    ],
    ...overrides,
  };
}

function findButtonByText(wrapper: VueWrapper<InstanceType<typeof AnalyzePage>>, label: string) {
  const button = wrapper.findAll('button').find((item) => item.text().trim() === label);
  if (!button) {
    throw new Error(`Button "${label}" not found`);
  }
  return button;
}

async function mountPage() {
  const wrapper = mount(AnalyzePage, {
    global: {
      stubs: {
        AutoComplete: AutoCompleteStub,
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        DatePicker: DatePickerStub,
        InputText: InputTextStub,
        Message: { template: '<div><slot /></div>' },
        MetricGrid: { template: '<div />' },
        PageHeader: { template: '<div><slot name="actions" /></div>' },
        ReportMarkdown: { template: '<div />' },
        RunHistoryConfirmDialog: RunHistoryConfirmDialogStub,
        Select: SelectStub,
        Tag: { props: ['value', 'severity'], template: '<span>{{ value }}</span>' },
      },
    },
  });

  await flushPromises();
  await wrapper.get('[data-testid="select-stock"]').trigger('click');
  await flushPromises();
  return wrapper;
}

describe('AnalyzePage', () => {
  beforeEach(() => {
    // Keep the recent-history fixtures inside the local confirmation window.
    vi.useFakeTimers({ toFake: ['Date'] });
    vi.setSystemTime(new Date('2026-07-05T09:00:00+08:00'));
    apiGet.mockReset();
    apiPost.mockReset();
    push.mockReset();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('creates a run immediately when the ticker has no recent history and no active run', async () => {
    apiGet.mockImplementation((path: string) => {
      if (path.startsWith('/api/runs/ticker-history')) {
        return Promise.resolve({ ticker: 'AAPL', has_active_run: false, page: 1, page_size: 10, total_count: 0, items: [] });
      }
      return resolveAnalyzeBootPayload(path);
    });
    apiPost.mockResolvedValueOnce({ run_id: 'run-1', status: 'queued', ticker: 'AAPL', date: '2026-07-05' });

    const wrapper = await mountPage();
    await findButtonByText(wrapper, '开始分析').trigger('click');
    await flushPromises();

    expect(apiPost).toHaveBeenCalledWith('/api/runs', expect.objectContaining({ ticker: 'AAPL' }), session.apiContext.value);
  });

  it('opens a confirmation dialog when the ticker was analyzed in the recent local window', async () => {
    apiGet.mockImplementation((path: string) => {
      if (path.startsWith('/api/runs/ticker-history')) {
        return Promise.resolve(sampleRecentHistoryPage());
      }
      return resolveAnalyzeBootPayload(path);
    });

    const wrapper = await mountPage();
    await findButtonByText(wrapper, '开始分析').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('启动新的分析');
    expect(apiPost).not.toHaveBeenCalled();
  });

  it('blocks creation and offers view-now when the ticker has an active run', async () => {
    apiGet.mockImplementation((path: string) => {
      if (path.startsWith('/api/runs/ticker-history')) {
        return Promise.resolve(sampleRecentHistoryPage({
          has_active_run: true,
          active_run_id: 'run-active',
          active_run_status: 'running',
        }));
      }
      return resolveAnalyzeBootPayload(path);
    });

    const wrapper = await mountPage();
    await findButtonByText(wrapper, '开始分析').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('立即查看');
    expect(apiPost).not.toHaveBeenCalled();
  });

  it('navigates to the selected history row from the dialog', async () => {
    apiGet.mockImplementation((path: string) => {
      if (path.startsWith('/api/runs/ticker-history')) {
        return Promise.resolve(sampleRecentHistoryPage());
      }
      return resolveAnalyzeBootPayload(path);
    });

    const wrapper = await mountPage();
    await findButtonByText(wrapper, '开始分析').trigger('click');
    await flushPromises();
    await wrapper.get('[data-testid="history-dialog-row"]').trigger('click');

    expect(push).toHaveBeenCalledWith({ name: 'run-detail', params: { runId: 'run-recent' } });
  });

  it('reopens the active-run dialog when create hits a structured 409 conflict after preflight', async () => {
    let historyCalls = 0;
    apiGet.mockImplementation((path: string) => {
      if (path.startsWith('/api/runs/ticker-history')) {
        historyCalls += 1;
        return Promise.resolve(
          historyCalls === 1
            ? sampleRecentHistoryPage()
            : sampleRecentHistoryPage({ has_active_run: true, active_run_id: 'run-active', active_run_status: 'running' }),
        );
      }
      return resolveAnalyzeBootPayload(path);
    });
    apiPost.mockRejectedValueOnce(Object.assign(
      new Error('AAPL already has an active analysis run.'),
      {
        status: 409,
        detail: {
          code: 'ticker_active_run_exists',
          active_run_id: 'run-active',
          active_run_status: 'running',
        },
      },
    ));

    const wrapper = await mountPage();
    await findButtonByText(wrapper, '开始分析').trigger('click');
    await flushPromises();
    await wrapper.get('[data-testid="history-dialog-confirm"]').trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('立即查看');
    expect(apiGet.mock.calls.filter(([path]) => String(path).startsWith('/api/runs/ticker-history'))).toHaveLength(2);
  });
});
