import { mount } from '@vue/test-utils';
import PrimeVue from 'primevue/config';
import DatePicker from 'primevue/datepicker';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import UserFormDialog from './UserFormDialog.vue';

function mountForm(expiresAt = '') {
  return mount(UserFormDialog, {
    props: { visible: true, mode: 'edit', user: { username: 'alice', expires_at: expiresAt } },
    global: {
      plugins: [PrimeVue],
      stubs: { Select: true, Dialog: { template: '<div><slot /><slot name="footer" /></div>' } },
    },
  });
}

describe('UserFormDialog expiry picker', () => {
  beforeEach(() => {
    vi.stubGlobal('matchMedia', () => ({ matches: false, addEventListener() {}, removeEventListener() {} }));
  });
  it('round trips local expiry dates without shifting the submitted time', async () => {
    const wrapper = mountForm('2026-11-13T09:30');
    const picker = wrapper.findComponent(DatePicker);
    expect(picker.exists()).toBe(true);
    expect(picker.props('modelValue')).toEqual(new Date(2026, 10, 13, 9, 30));
    picker.vm.$emit('update:modelValue', new Date(2026, 11, 1, 23, 45));
    await wrapper.get('[data-testid="submit-user-form"]').trigger('click');
    expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({ expires_at: '2026-12-01T23:45' });
  });

  it('submits an empty expiry when the picker is cleared', async () => {
    const wrapper = mountForm('2026-11-13T09:30');
    const picker = wrapper.findComponent(DatePicker);
    expect(picker.exists()).toBe(true);
    picker.vm.$emit('update:modelValue', null);
    await wrapper.get('[data-testid="submit-user-form"]').trigger('click');
    expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({ expires_at: '' });
  });
});
