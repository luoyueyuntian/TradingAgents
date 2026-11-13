import { mount } from '@vue/test-utils';
import PrimeVue from 'primevue/config';
import DatePicker from 'primevue/datepicker';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import DateTimeInput from './DateTimeInput.vue';

const wrappers: ReturnType<typeof mount>[] = [];

function mountPicker(props: { modelValue: string; mode?: 'date' | 'datetime' | 'time'; separator?: 'T' | ' '; disabled?: boolean }) {
  const wrapper = mount(DateTimeInput, { props: { ...props, appendTo: 'self' }, attachTo: document.body, global: { plugins: [PrimeVue] } });
  wrappers.push(wrapper);
  return wrapper;
}

describe('DateTimeInput local form values', () => {
  beforeEach(() => {
    vi.stubGlobal('matchMedia', () => ({ matches: false, addEventListener() {}, removeEventListener() {} }));
  });

  afterEach(() => {
    wrappers.splice(0).forEach((wrapper) => wrapper.unmount());
    vi.unstubAllGlobals();
  });

  it('keeps date-only values on the selected local calendar day', async () => {
    const wrapper = mountPicker({ modelValue: '2026-11-13' });
    const picker = wrapper.getComponent(DatePicker);
    expect(picker.props('modelValue')).toEqual(new Date(2026, 10, 13));
    // Local midnight and late evening would shift a day if serialized as UTC.
    picker.vm.$emit('update:modelValue', new Date(2026, 10, 14, 0, 0));
    picker.vm.$emit('update:modelValue', new Date(2026, 10, 14, 23, 59));
    expect(wrapper.emitted('update:modelValue')).toEqual([['2026-11-14'], ['2026-11-14']]);
    await wrapper.setProps({ modelValue: '' });
    expect(picker.props('modelValue')).toBeNull();
  });

  it('preserves the space-separated schedule format for one-time tasks', async () => {
    const wrapper = mountPicker({ modelValue: '2026-11-13 21:30', mode: 'datetime', separator: ' ' });
    expect(wrapper.getComponent(DatePicker).props('modelValue')).toEqual(new Date(2026, 10, 13, 21, 30));
    await wrapper.get('input').setValue('2026-12-01 09:05');
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['2026-12-01 09:05']);
  });

  it('submits only hours and minutes for recurring rules', async () => {
    const wrapper = mountPicker({ modelValue: '09:00', mode: 'time' });
    expect(wrapper.get('input').element.value).toBe('09:00');
    await wrapper.get('input').setValue('23:45');
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['23:45']);
  });

  it('opens a calendar, accepts a selected day, and clears an optional value', async () => {
    const wrapper = mountPicker({ modelValue: '2026-11-13' });
    await wrapper.get('input').trigger('focus');
    const day = wrapper.findAll('[data-pc-section="day"]').find((item) => item.text() === '20' && !item.attributes('data-p-other-month'));
    expect(day).toBeDefined();
    await day!.trigger('click');
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['2026-11-20']);
    await wrapper.get('input').trigger('focus');
    await wrapper.get('[aria-label="Clear"]').trigger('click');
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['']);
  });

  it.each([
    { mode: 'datetime' as const, value: '2026-02-30 09:00' },
    { mode: 'datetime' as const, value: '2026-11-13 25:00' },
    { mode: 'time' as const, value: '12:99' },
  ])('ignores invalid manual input: $value', async ({ mode, value }) => {
    const wrapper = mountPicker({ modelValue: '', mode });
    await wrapper.get('input').setValue(value);
    expect(wrapper.emitted('update:modelValue')).toBeUndefined();
  });

  it('keeps disabled inputs disabled', () => {
    const wrapper = mountPicker({ modelValue: '2026-11-13', disabled: true });
    expect(wrapper.get('input').element.disabled).toBe(true);
  });
});
