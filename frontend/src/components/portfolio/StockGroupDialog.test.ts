import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import StockGroupDialog from './StockGroupDialog.vue';

const { apiPost, apiPatch } = vi.hoisted(() => ({
  apiPost: vi.fn(),
  apiPatch: vi.fn(),
}));

vi.mock('../../services/api', () => ({
  apiPost,
  apiPatch,
}));

vi.mock('../../stores/session', () => ({
  useSession: () => ({
    apiContext: { value: { tenantId: 'tenant-a', apiToken: 'token-a' } },
  }),
}));

const InputTextStub = {
  props: ['modelValue'],
  emits: ['update:modelValue'],
  template: '<input :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)">',
};

const PortfolioDialogStub = {
  props: ['visible', 'title', 'saveLabel', 'cancelLabel', 'loading', 'disabled', 'error'],
  emits: ['update:visible', 'submit'],
  template: `
    <div>
      <slot />
      <button data-testid="submit" :disabled="disabled" @click="$emit('submit')">{{ saveLabel }}</button>
    </div>
  `,
};

const PortfolioStockPickerStub = {
  props: ['selectedStock', 'stockMarket', 'disabled'],
  emits: ['update:selectedStock', 'update:stockMarket'],
  template: '<div data-testid="stock-picker-stub" />',
};

const ButtonStub = {
  props: ['label', 'disabled'],
  emits: ['click'],
  template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}<slot /></button>',
};

describe('StockGroupDialog', () => {
  beforeEach(() => {
    apiPost.mockReset();
    apiPatch.mockReset();
    apiPost.mockResolvedValue({});
    apiPatch.mockResolvedValue({});
  });

  it('creates an empty group without showing the stock picker in create mode', async () => {
    const wrapper = mount(StockGroupDialog, {
      props: {
        visible: true,
        mode: 'create',
        group: null,
      },
      global: {
        stubs: {
          InputText: InputTextStub,
          PortfolioDialog: PortfolioDialogStub,
          PortfolioStockPicker: PortfolioStockPickerStub,
          Button: ButtonStub,
        },
      },
    });

    expect(wrapper.find('[data-testid="stock-picker-stub"]').exists()).toBe(false);

    await wrapper.get('input').setValue('AI Leaders');
    await wrapper.get('[data-testid="submit"]').trigger('click');
    await flushPromises();

    expect(apiPost).toHaveBeenCalledWith(
      '/api/stock-groups',
      { name: 'AI Leaders', tickers: [] },
      { tenantId: 'tenant-a', apiToken: 'token-a' },
    );
  });

  it('shows the stock picker in edit mode', () => {
    const wrapper = mount(StockGroupDialog, {
      props: {
        visible: true,
        mode: 'edit',
        group: { id: 'group-1', name: 'AI Leaders', tickers: [] },
      },
      global: {
        stubs: {
          InputText: InputTextStub,
          PortfolioDialog: PortfolioDialogStub,
          PortfolioStockPicker: PortfolioStockPickerStub,
          Button: ButtonStub,
        },
      },
    });

    expect(wrapper.find('[data-testid="stock-picker-stub"]').exists()).toBe(true);
  });

  it('shows selected company names instead of tickers when adding stocks in edit mode', async () => {
    const wrapper = mount(StockGroupDialog, {
      props: {
        visible: true,
        mode: 'edit',
        group: { id: 'group-1', name: 'AI Leaders', tickers: [], company_names: {} },
      },
      global: {
        stubs: {
          InputText: InputTextStub,
          PortfolioDialog: PortfolioDialogStub,
          PortfolioStockPicker: {
            props: ['selectedStock', 'stockMarket', 'disabled'],
            emits: ['update:selectedStock', 'update:stockMarket'],
            template: '<button data-testid="pick-stock" @click="$emit(\'update:selectedStock\', { market: \'us\', symbol: \'NVDA\', name: \'NVIDIA Corporation\', exchange: \'NASDAQ\', label: \'NVDA · NVIDIA Corporation\' })">pick</button>',
          },
          Button: ButtonStub,
        },
      },
    });

    await wrapper.get('[data-testid="pick-stock"]').trigger('click');
    await wrapper.get('[data-testid="stock-group-add-ticker"]').trigger('click');

    expect(wrapper.text()).toContain('NVIDIA Corporation');
    expect(wrapper.text()).not.toContain('NVDA x');
  });
});
