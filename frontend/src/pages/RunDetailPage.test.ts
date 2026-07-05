import { flushPromises, mount, type VueWrapper } from '@vue/test-utils';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import RunDetailPage from './RunDetailPage.vue';

const { formatDateTime } = vi.hoisted(() => ({
  formatDateTime: vi.fn((value: unknown) => `LOCAL:${String(value)}`),
}));

const { apiDelete, apiGet, apiPatch, apiPost, buildApiUrl } = vi.hoisted(() => ({
  apiDelete: vi.fn(),
  apiGet: vi.fn(),
  apiPatch: vi.fn(),
  apiPost: vi.fn(),
  buildApiUrl: vi.fn((path: string) => path),
}));

vi.mock('../services/api', () => ({
  apiDelete,
  apiGet,
  apiPatch,
  apiPost,
  buildApiUrl,
}));

vi.mock('../utils/format', async () => {
  const actual = await vi.importActual<typeof import('../utils/format')>('../utils/format');
  return {
    ...actual,
    formatDateTime,
  };
});

const push = vi.fn();
const route = {
  params: {
    runId: 'source-run',
  },
};

vi.mock('vue-router', () => ({
  useRoute: () => route,
  useRouter: () => ({
    push,
  }),
}));

const session = {
  apiContext: { value: { tenantId: 'tenant-a' } },
  canWrite: { value: true },
  state: {
    currentMemberId: 'member-1',
  },
};

vi.mock('../stores/session', () => ({
  useSession: () => session,
}));

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type', 'icon', 'severity', 'outlined', 'text'],
  template: `
    <button :type="type || 'button'" :disabled="disabled" @click="$emit('click', $event)">
      {{ label }}<slot />
    </button>
  `,
};

const CardStub = {
  template: '<div><slot name="title" /><slot name="content" /></div>',
};

const DatePickerStub = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: '<div />',
};

const InputTextStub = {
  props: ['modelValue', 'type', 'placeholder', 'disabled'],
  emits: ['update:modelValue'],
  template: '<input :value="modelValue" :type="type || \'text\'" :placeholder="placeholder" :disabled="disabled">',
};

const SelectStub = {
  props: ['modelValue', 'options', 'optionLabel', 'optionValue', 'placeholder', 'disabled'],
  emits: ['update:modelValue', 'change'],
  template: '<select :value="modelValue" :disabled="disabled"></select>',
};

const TextareaStub = {
  props: ['modelValue', 'rows', 'placeholder', 'disabled'],
  emits: ['update:modelValue'],
  template: '<textarea :value="modelValue" :rows="rows" :placeholder="placeholder" :disabled="disabled"></textarea>',
};

function makeRun(status: string) {
  return {
    run_id: 'source-run',
    status,
    ticker: 'AAPL',
    company_name: 'Apple Inc.',
    date: '2026-07-04',
    asset_type: 'stock',
    created_at: '2026-07-04T09:00:00',
    started_at: null,
    completed_at: status === 'completed' ? '2026-07-04T09:05:00' : null,
    queue_position: null,
    agents: {},
    report_sections: {
      final_trade_decision: 'Hold',
    },
    config_summary: {
      llm_provider: 'openai',
    },
    current_report: '',
    final_report: '',
    signal: status === 'completed' ? 'Hold' : null,
    error: status === 'failed' ? 'Vendor timeout' : null,
    annotation: null,
    review: null,
    public_share: {
      url: 'https://example.com/share/source-run',
      expires_at: '2026-07-05T09:00:00Z',
      view_count: 3,
    },
  };
}

function mockDetailApis(status: string) {
  const run = makeRun(status);
  apiGet.mockImplementation((path: string) => {
    switch (path) {
      case '/api/runs/source-run':
        return Promise.resolve(run);
      case '/api/runs/source-run/artifacts':
        return Promise.resolve([]);
      case '/api/pinned-runs':
        return Promise.resolve([]);
      case '/api/runs/source-run/comments':
        return Promise.resolve([
          {
            id: 'comment-1',
            author: 'Alice',
            created_at: '2026-07-04T09:30:00Z',
            content: 'Need a follow-up check.',
            resolved: false,
          },
        ]);
      case '/api/members':
        return Promise.resolve([{ id: 'member-1', name: 'Alice' }]);
      case '/api/runs':
        return Promise.resolve([run]);
      default:
        throw new Error(`Unexpected apiGet path: ${path}`);
    }
  });
}

function findButtonByText(wrapper: VueWrapper<InstanceType<typeof RunDetailPage>>, label: string) {
  const button = wrapper.findAll('button').find((item) => item.text().trim() === label);
  if (!button) {
    throw new Error(`Button "${label}" not found`);
  }
  return button;
}

async function mountPage(status: string, options: { setupApis?: boolean } = {}) {
  if (options.setupApis !== false) {
    mockDetailApis(status);
  }
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: true,
    text: () => Promise.resolve('terminal output'),
  }));

  const wrapper = mount(RunDetailPage, {
    global: {
      stubs: {
        Button: ButtonStub,
        Card: CardStub,
        DatePicker: DatePickerStub,
        InputText: InputTextStub,
        Message: { template: '<div><slot /></div>' },
        MetricGrid: { template: '<div />' },
        OverlayBadge: { template: '<div><slot /></div>' },
        PageHeader: { template: '<div><slot name="actions" /></div>' },
        ReportMarkdown: { template: '<div />' },
        Select: SelectStub,
        Tag: { props: ['value', 'severity'], template: '<span>{{ value }}</span>' },
        Textarea: TextareaStub,
      },
    },
  });

  await flushPromises();
  return wrapper;
}

describe('RunDetailPage', () => {
  beforeEach(() => {
    apiDelete.mockReset();
    apiGet.mockReset();
    apiPatch.mockReset();
    apiPost.mockReset();
    buildApiUrl.mockClear();
    push.mockReset();
    formatDateTime.mockClear();
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('asks for confirmation before retrying a completed run', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    const wrapper = await mountPage('completed');

    await findButtonByText(wrapper, '重试').trigger('click');
    await flushPromises();

    expect(confirmSpy).toHaveBeenCalledWith(expect.stringContaining('Apple Inc.'));
    expect(apiPost).not.toHaveBeenCalled();
    expect(push).not.toHaveBeenCalled();
  });

  it('retries failed runs immediately without confirmation', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
    apiPost.mockResolvedValue({
      run_id: 'retry-run',
      status: 'queued',
      ticker: 'AAPL',
      company_name: 'Apple Inc.',
      date: '2026-07-04',
    });
    const wrapper = await mountPage('failed');

    await findButtonByText(wrapper, '重试').trigger('click');
    await flushPromises();

    expect(confirmSpy).not.toHaveBeenCalled();
    expect(apiPost).toHaveBeenCalledWith(
      '/api/runs/source-run/retry',
      {},
      session.apiContext.value,
    );
    expect(push).toHaveBeenCalledWith({ name: 'run-detail', params: { runId: 'retry-run' } });
  });

  it('renders run comment and public share timestamps through the shared local formatter', async () => {
    const wrapper = await mountPage('completed');

    expect(wrapper.text()).toContain('LOCAL:2026-07-04T09:30:00Z');
    expect(wrapper.text()).toContain('LOCAL:2026-07-05T09:00:00Z');
  });

  it('polls run detail every 5 seconds while the analysis is still running', async () => {
    vi.useFakeTimers();
    const run = makeRun('running');
    apiGet.mockImplementation((path: string) => {
      switch (path) {
        case '/api/runs/source-run':
          return Promise.resolve({ ...run });
        case '/api/runs/source-run/artifacts':
          return Promise.resolve([]);
        case '/api/pinned-runs':
          return Promise.resolve([]);
        case '/api/runs/source-run/comments':
          return Promise.resolve([]);
        case '/api/members':
          return Promise.resolve([{ id: 'member-1', name: 'Alice' }]);
        case '/api/runs':
          return Promise.resolve([{ ...run }]);
        default:
          throw new Error(`Unexpected apiGet path: ${path}`);
      }
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve('terminal output'),
    }));

    await mountPage('running', { setupApis: false });
    expect(apiGet).toHaveBeenCalledWith('/api/runs/source-run', session.apiContext.value);

    await vi.advanceTimersByTimeAsync(5000);
    await flushPromises();

    const detailCalls = apiGet.mock.calls.filter(([path]) => path === '/api/runs/source-run');
    expect(detailCalls).toHaveLength(2);

    await vi.advanceTimersByTimeAsync(5000);
    await flushPromises();

    const nextDetailCalls = apiGet.mock.calls.filter(([path]) => path === '/api/runs/source-run');
    expect(nextDetailCalls).toHaveLength(3);
  });

  it('stops polling once the run reaches a terminal status', async () => {
    vi.useFakeTimers();
    const statuses = ['running', 'completed'];
    let detailIndex = -1;
    apiGet.mockImplementation((path: string) => {
      if (path === '/api/runs/source-run') {
        detailIndex += 1;
        return Promise.resolve(makeRun(statuses[Math.min(detailIndex, statuses.length - 1)]));
      }

      const currentRun = makeRun(statuses[Math.max(detailIndex, 0)]);
      switch (path) {
        case '/api/runs/source-run/artifacts':
          return Promise.resolve([]);
        case '/api/pinned-runs':
          return Promise.resolve([]);
        case '/api/runs/source-run/comments':
          return Promise.resolve([]);
        case '/api/members':
          return Promise.resolve([{ id: 'member-1', name: 'Alice' }]);
        case '/api/runs':
          return Promise.resolve([currentRun]);
        default:
          throw new Error(`Unexpected apiGet path: ${path}`);
      }
    });
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      text: () => Promise.resolve('terminal output'),
    }));

    await mountPage('running', { setupApis: false });

    await vi.advanceTimersByTimeAsync(5000);
    await flushPromises();

    let detailCalls = apiGet.mock.calls.filter(([path]) => path === '/api/runs/source-run');
    expect(detailCalls).toHaveLength(2);

    await vi.advanceTimersByTimeAsync(5000);
    await flushPromises();

    detailCalls = apiGet.mock.calls.filter(([path]) => path === '/api/runs/source-run');
    expect(detailCalls).toHaveLength(2);
  });
});
