<template>
  <DatePicker
    v-model="dateValue"
    date-format="yy-mm-dd"
    :show-time="mode === 'datetime'"
    :time-only="mode === 'time'"
    hour-format="24"
    show-icon
    icon-display="input"
    show-button-bar
    :manual-input="true"
    fluid
    @input="handleTimeInput"
  />
</template>

<script setup lang="ts">
import DatePicker from 'primevue/datepicker';
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  modelValue: string;
  mode?: 'date' | 'datetime' | 'time';
  separator?: 'T' | ' ';
}>(), {
  mode: 'date',
  separator: 'T',
});

const emit = defineEmits<{
  (e: 'update:modelValue', value: string): void;
}>();

const pad = (value: number) => String(value).padStart(2, '0');
const localDate = (value: Date) => `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}`;
const localTime = (value: Date) => `${pad(value.getHours())}:${pad(value.getMinutes())}`;

// Form values represent local wall-clock times. Date-only strings must not
// be parsed as UTC, and serializing them must not go through toISOString().
const dateValue = computed<Date | null>({
  get() {
    if (!props.modelValue) return null;
    const value = props.mode === 'time'
      ? `2000-01-01T${props.modelValue}`
      : props.mode === 'date'
        ? `${props.modelValue}T00:00`
        : props.modelValue.replace(' ', 'T');
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  },
  set(value) {
    if (!value || Number.isNaN(value.getTime())) {
      emit('update:modelValue', '');
      return;
    }
    const date = localDate(value);
    const time = localTime(value);
    emit('update:modelValue', props.mode === 'time'
      ? time
      : props.mode === 'datetime' ? `${date}${props.separator}${time}` : date);
  },
});

// PrimeVue 4.5.5's 24-hour manual parser expects an AM/PM token and silently
// rejects HH:mm. Handle its input event without changing the calendar controls.
function handleTimeInput(event: Event) {
  if (props.mode === 'date') return;
  const text = (event.target as HTMLInputElement).value.trim();
  const normalized = props.mode === 'time' ? `2000-01-01T${text}` : text.replace(' ', 'T');
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(normalized)) return;
  const value = new Date(normalized);
  if (Number.isNaN(value.getTime()) || `${localDate(value)}T${localTime(value)}` !== normalized) return;
  dateValue.value = value;
}
</script>
