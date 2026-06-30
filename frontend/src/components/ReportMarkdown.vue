<template>
  <div v-if="blocks.length" class="report-markdown">
    <template v-for="(block, blockIndex) in blocks" :key="`${block.kind}-${blockIndex}`">
      <component :is="headingTag(block.level)" v-if="block.kind === 'heading'" class="report-heading">
        <template v-for="(segment, segmentIndex) in block.content" :key="segmentIndex">
          <strong v-if="segment.kind === 'strong'">{{ segment.text }}</strong>
          <template v-else>{{ segment.text }}</template>
        </template>
      </component>

      <p v-else-if="block.kind === 'paragraph'" class="report-paragraph">
        <template v-for="(segment, segmentIndex) in block.content" :key="segmentIndex">
          <strong v-if="segment.kind === 'strong'">{{ segment.text }}</strong>
          <template v-else>{{ segment.text }}</template>
        </template>
      </p>

      <ul v-else-if="block.kind === 'list'" class="report-list">
        <li v-for="(item, itemIndex) in block.items" :key="itemIndex">
          <template v-for="(segment, segmentIndex) in item" :key="segmentIndex">
            <strong v-if="segment.kind === 'strong'">{{ segment.text }}</strong>
            <template v-else>{{ segment.text }}</template>
          </template>
        </li>
      </ul>

      <div v-else-if="block.kind === 'table'" class="report-table-wrap">
        <table class="report-table">
          <thead>
            <tr>
              <th v-for="(header, headerIndex) in block.headers" :key="headerIndex">{{ header }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
              <td v-for="(cell, cellIndex) in normalizedRow(row, block.headers.length)" :key="cellIndex">{{ cell }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <pre v-else-if="block.kind === 'code'" class="report-code">{{ block.text }}</pre>
    </template>
  </div>
  <p v-else class="muted">{{ emptyText }}</p>
</template>

<script setup lang="ts">
import { computed } from 'vue';

import { parseReportMarkdown } from '../utils/reportMarkdown';

const props = defineProps<{
  content?: string | null;
  emptyText: string;
}>();

const blocks = computed(() => parseReportMarkdown(props.content || ''));

function headingTag(level?: number) {
  const resolved = Math.min(Math.max(level || 3, 2), 4);
  return `h${resolved}`;
}

function normalizedRow(row: string[], length: number): string[] {
  return Array.from({ length }, (_, index) => row[index] || '');
}
</script>
