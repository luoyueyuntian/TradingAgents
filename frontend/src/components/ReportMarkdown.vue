<template>
  <div
    v-if="blocks.length"
    class="uno-max-h-[680px] uno-overflow-auto uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-[1.05rem] uno-leading-[1.6] uno-text-[#162326]"
  >
    <template v-for="(block, blockIndex) in blocks" :key="`${block.kind}-${blockIndex}`">
      <component :is="headingTag(block.level)" v-if="block.kind === 'heading'" :class="headingClass(block.level, blockIndex)">
        <template v-for="(segment, segmentIndex) in block.content" :key="segmentIndex">
          <strong v-if="segment.kind === 'strong'">{{ segment.text }}</strong>
          <template v-else>{{ segment.text }}</template>
        </template>
      </component>

      <p v-else-if="block.kind === 'paragraph'" class="uno-mb-[0.8rem] uno-mt-0">
        <template v-for="(segment, segmentIndex) in block.content" :key="segmentIndex">
          <strong v-if="segment.kind === 'strong'">{{ segment.text }}</strong>
          <template v-else>{{ segment.text }}</template>
        </template>
      </p>

      <ul v-else-if="block.kind === 'list'" class="uno-mb-[0.85rem] uno-mt-0 uno-pl-[1.2rem]">
        <li v-for="(item, itemIndex) in block.items" :key="itemIndex" :class="itemIndex > 0 ? 'uno-mt-[0.35rem]' : ''">
          <template v-for="(segment, segmentIndex) in item" :key="segmentIndex">
            <strong v-if="segment.kind === 'strong'">{{ segment.text }}</strong>
            <template v-else>{{ segment.text }}</template>
          </template>
        </li>
      </ul>

      <div v-else-if="block.kind === 'table'" class="uno-my-3 uno-mb-4 uno-overflow-x-auto uno-rounded-lg uno-border uno-border-[#d9e5e5]">
        <table class="uno-w-full uno-min-w-[520px] uno-border-collapse uno-text-left uno-text-[0.92rem]">
          <thead>
            <tr>
              <th
                v-for="(header, headerIndex) in block.headers"
                :key="headerIndex"
                class="uno-border-b uno-border-[#e5eeee] uno-bg-[#eef4f4] uno-px-3 uno-py-[0.65rem] uno-text-left uno-align-top uno-font-700 uno-text-[#243a3d]"
              >
                {{ header }}
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, rowIndex) in block.rows" :key="rowIndex">
              <td
                v-for="(cell, cellIndex) in normalizedRow(row, block.headers.length)"
                :key="cellIndex"
                :class="[
                  'uno-px-3 uno-py-[0.65rem] uno-text-left uno-align-top',
                  rowIndex === block.rows.length - 1 ? 'uno-border-b-0' : 'uno-border-b uno-border-[#e5eeee]',
                ]"
              >
                {{ cell }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <pre v-else-if="block.kind === 'code'" class="uno-mb-[0.85rem] uno-mt-0 uno-overflow-auto uno-rounded-lg uno-bg-[#101b1d] uno-p-3 uno-text-[#d8f3ee]">{{ block.text }}</pre>
    </template>
  </div>
  <p v-else class="uno-text-[#6f8183]">{{ emptyText }}</p>
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

function headingClass(level?: number, index = 0) {
  const sizeClass = level === 2 ? 'uno-text-[1.2rem]' : level === 3 ? 'uno-text-[1.05rem]' : 'uno-text-[0.95rem]';
  return [
    index === 0 ? 'uno-mt-0' : 'uno-mt-[1.1rem]',
    'uno-mb-[0.45rem] uno-text-[#102224] uno-tracking-normal',
    sizeClass,
  ];
}

function normalizedRow(row: string[], length: number): string[] {
  return Array.from({ length }, (_, index) => row[index] || '');
}
</script>
