import { flushPromises, mount } from '@vue/test-utils';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import PortfolioAlertsPage from './PortfolioAlertsPage.vue';

const { apiGet, apiDelete } = vi.hoisted(() => ({
  apiGet: vi.fn(),
  apiDelete: vi.fn(),
}));

vi.mock('../services/api', () => ({
  apiGet,
  apiDelete,
}));

vi.mock('../stores/session', () => ({
  useSession: () => ({
    apiContext: { value: { tenantId: 'tenant-a', apiToken: 'token-a' } },
    canWrite: { value: true },
  }),
}));

describe('PortfolioAlertsPage', () => {
  beforeEach(() => {
    apiGet.mockReset();
    apiDelete.mockReset();
    apiGet.mockResolvedValue({
      rules: [{ id: 'alert-1', ticker: 'NVDA', company_name: 'NVIDIA Corporation', field: 'signal', value: 'Buy' }],
      hits: [{ rule_id: 'alert-1', ticker: 'NVDA', company_name: 'NVIDIA Corporation', field: 'signal', expected_value: 'Buy', actual_value: 'Buy', run_id: 'run-1', run_date: '2026-01-15' }],
    });
  });

  it('loads alert rules and deletes one row', async () => {
    const wrapper = mount(PortfolioAlertsPage, {
      global: {
        stubs: {
          Button: { props: ['label', 'disabled'], emits: ['click'], template: '<button :disabled="disabled" @click="$emit(\'click\')">{{ label }}<slot /></button>' },
          Message: { template: '<div><slot /></div>' },
          MetricGrid: { props: ['items'], template: '<div>{{ items.length }}</div>' },
          PageHeader: { template: '<div><slot name="actions" /></div>' },
          PortfolioSubnav: { template: '<nav />' },
          AlertDialog: { props: ['visible'], emits: ['update:visible', 'saved'], template: '<div />' },
        },
      },
    });

    await flushPromises();
    expect(apiGet).toHaveBeenCalledWith('/api/alerts', { tenantId: 'tenant-a', apiToken: 'token-a' });
    expect(wrapper.text()).toContain('NVDA');
    expect(wrapper.text()).toContain('NVIDIA Corporation');
    await wrapper.get('[data-testid="alert-delete-alert-1"]').trigger('click');
    expect(apiDelete).toHaveBeenCalledWith('/api/alerts/rules/alert-1', { tenantId: 'tenant-a', apiToken: 'token-a' });
  });
});
