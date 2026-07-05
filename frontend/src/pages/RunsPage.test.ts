import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import RunsPage from './RunsPage.vue';

const { apiGet } = vi.hoisted(() => ({
  apiGet: vi.fn(),
}));

vi.mock('../services/api', () => ({
  apiGet,
}));

const push = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push,
  }),
}));

const session = {
  apiContext: { value: { tenantId: 'tenant-a' } },
};

vi.mock('../stores/session', () => ({
  useSession: () => session,
}));

const ButtonStub = {
  props: ['label', 'disabled', 'loading', 'type', 'icon', 'severity'],
  template: `
    <button :type="type || 'button'" :disabled="disabled" @click="$emit('click', $event)">
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
      @change="$emit('update:modelValue', $event.target.value); $emit('change', $event)"
    >
      <option v-for="option in options" :key="option[optionValue || 'value']" :value="option[optionValue || 'value']">
        {{ option[optionLabel || 'label'] }}
      </option>
    </select>
  `,
};

const DataTableStub = {
  props: ['value'],
  template: `
    <div>
      <button
        v-for="item in value"
        :key="item.run_id"
        type="button"
        data-testid="run-row"
        @click="$emit('row-click', { data: item })"
      >
        {{ item.run_id }}
      </button>
      <slot />
    </div>
  `,
};

function mountPage() {
  return mount(RunsPage, {
    global: {
      stubs: {
        Button: ButtonStub,
        Card: { template: '<div><slot name="title" /><slot name="content" /></div>' },
        Column: { props: ['field', 'header'], template: '<div data-testid="column-field">{{ field }} {{ header }}<slot /></div>' },
        DataTable: DataTableStub,
        InputText: InputTextStub,
        Message: { template: '<div><slot /></div>' },
        PageHeader: { template: '<div><slot name="actions" /></div>' },
        Select: SelectStub,
        Tag: { template: '<span><slot /></span>' },
      },
    },
  });
}

describe('RunsPage', () => {
  beforeEach(() => {
    apiGet.mockReset();
    push.mockReset();
  });

  it('loads company groups and resets to page 1 when the search filter changes', async () => {
    apiGet.mockResolvedValue({ items: [], page: 2, page_size: 20, total_count: 0 });

    const wrapper = mountPage();
    await flushPromises();

    await wrapper.get('input').setValue('apple');
    await flushPromises();

    expect(apiGet).toHaveBeenLastCalledWith(
      '/api/runs/company-groups?q=apple&archived=active&page=1&page_size=20',
      session.apiContext.value,
    );
  });

  it('renders company group cards and opens run details from grouped rows', async () => {
    apiGet.mockResolvedValue({
      items: [
        {
          group_key: 'apple-inc-stock',
          company_name: 'Apple Inc.',
          asset_type: 'stock',
          tickers: ['AAPL'],
          run_count: 2,
          latest_created_at: '2026-07-04T09:00:00',
          recent_runs: [
            { run_id: 'run-1', ticker: 'AAPL', date: '2026-07-04', status: 'completed', signal: 'Buy', llm_provider: 'openai' },
          ],
        },
      ],
      page: 1,
      page_size: 20,
      total_count: 1,
    });

    const wrapper = mountPage();
    await flushPromises();

    expect(wrapper.find('[data-testid="runs-company-group-card"]').exists()).toBe(true);
    expect(wrapper.text()).toContain('llm_provider');

    await wrapper.get('[data-testid="run-row"]').trigger('click');

    expect(push).toHaveBeenCalledWith({ name: 'run-detail', params: { runId: 'run-1' } });
  });
});
