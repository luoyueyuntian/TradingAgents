<template>
  <div class="uno-mb-4 uno-grid uno-grid-cols-[repeat(auto-fit,minmax(170px,1fr))] uno-gap-3">
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

defineProps<{
  items: Array<{
    label: string;
    value: string | number;
    detail?: string;
  }>;
}>();
</script>
