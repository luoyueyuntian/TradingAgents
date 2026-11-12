import { flushPromises, mount } from '@vue/test-utils';
import { describe, expect, it } from 'vitest';

import RunHistoryConfirmDialog from './RunHistoryConfirmDialog.vue';

const ButtonStub = {
  props: ['label', 'disabled', 'type', 'severity', 'outlined', 'icon'],
  emits: ['click'],
  template: `
    <button v-bind="$attrs" :type="type || 'button'" :disabled="disabled" @click="$emit('click', $event)">
      {{ label }}<slot />
    </button>
  `,
};

const DialogStub = {
  props: ['visible'],
  emits: ['update:visible'],
  template: '<div v-if="visible"><slot /><slot name="footer" /></div>',
};

const DataTableStub = {
  props: ['value'],
  emits: ['row-click'],
  template: `
    <div>
      <button
        v-for="item in value"
        :key="item.run_id"
        type="button"
        data-testid="history-row"
        @click="$emit('row-click', { data: item })"
      >
        {{ item.run_id }}
      </button>
      <slot />
    </div>
  `,
};

const ColumnStub = {
  props: ['field', 'header'],
  template: '<div data-testid="column-field">{{ field }} {{ header }}<slot /></div>',
};

const PaginatorStub = {
  props: ['rows', 'totalRecords', 'first'],
  emits: ['page'],
  template: '<button data-testid="next-page" type="button" @click="$emit(\'page\', { page: 1, first: rows, rows })">next</button>',
};

function samplePage() {
  return {
    ticker: 'AAPL',
    company_name: 'Apple Inc.',
    has_active_run: true,
    active_run_id: 'run-active',
    active_run_status: 'running',
    page: 1,
    page_size: 10,
    total_count: 12,
    items: [
      { run_id: 'run-active', ticker: 'AAPL', date: '2026-07-05', status: 'running', signal: null, research_depth: 5 },
    ],
  };
}

function mountDialog(mode: 'active' | 'recent-history') {
  return mount(RunHistoryConfirmDialog, {
    props: {
      visible: true,
      mode,
      historyPage: samplePage(),
      loading: false,
    },
    global: {
      stubs: {
        Button: ButtonStub,
        Column: ColumnStub,
        DataTable: DataTableStub,
        Dialog: DialogStub,
        Paginator: PaginatorStub,
        Tag: { props: ['value', 'severity'], template: '<span>{{ value }}</span>' },
      },
    },
  });
}

describe('RunHistoryConfirmDialog', () => {
  it('renders the active-run action set without a create button', async () => {
    const wrapper = mountDialog('active');
    await flushPromises();

    expect(wrapper.text()).toContain('立即查看');
    expect(wrapper.find('[data-testid="history-dialog-confirm"]').exists()).toBe(false);
  });

  it('renders the recent-history action set with the create button', async () => {
    const wrapper = mountDialog('recent-history');
    await flushPromises();

    expect(wrapper.text()).toContain('启动新的分析');
    expect(wrapper.text()).toContain('research_depth 深度');
  });

  it('emits row-open and page-change interactions', async () => {
    const wrapper = mountDialog('recent-history');
    await flushPromises();

    await wrapper.get('[data-testid="history-row"]').trigger('click');
    await wrapper.get('[data-testid="next-page"]').trigger('click');

    expect(wrapper.emitted('row-open')?.[0]?.[0]).toEqual(samplePage().items[0]);
    expect(wrapper.emitted('page-change')?.[0]?.[0]).toBe(2);
  });
});
