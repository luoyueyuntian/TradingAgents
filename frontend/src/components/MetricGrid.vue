<template>
  <div class="metric-grid">
    <Card v-for="item in items" :key="item.label" class="metric-card">
      <template #content>
        <span class="metric-label">{{ item.label }}</span>
        <strong class="metric-value">{{ item.value }}</strong>
        <small v-if="item.detail" class="metric-detail">{{ item.detail }}</small>
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
