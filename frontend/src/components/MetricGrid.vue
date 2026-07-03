<template>
  <div :class="gridClasses">
    <Card
      v-for="item in items"
      :key="item.label"
      :pt="{ body: { class: 'uno-p-[0.9rem]' }, content: { class: 'uno-grid uno-gap-1 uno-p-0' } }"
    >
      <template #content>
        <span class="uno-text-[0.78rem] uno-text-[#607174]">{{ item.label }}</span>
        <strong class="uno-text-xl uno-text-[#132a2d]">{{ item.value }}</strong>
        <small v-if="item.detail" class="uno-text-[#6f8183]">{{ item.detail }}</small>
      </template>
    </Card>
  </div>
</template>

<script setup lang="ts">
import Card from 'primevue/card';
import { computed } from 'vue';

const props = withDefaults(defineProps<{
  items: Array<{
    label: string;
    value: string | number;
    detail?: string;
  }>;
  layout?: 'default' | 'dashboard';
}>(), {
  layout: 'default',
});

const gridClasses = computed(() => [
  'uno-mb-4 uno-grid uno-gap-3',
  props.layout === 'dashboard'
    ? 'uno-grid-cols-4 max-[1100px]:uno-grid-cols-2 max-[640px]:uno-grid-cols-1'
    : 'uno-grid-cols-4 max-[1100px]:uno-grid-cols-2 max-[640px]:uno-grid-cols-1',
]);
</script>
