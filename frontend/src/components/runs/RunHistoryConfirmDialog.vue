<template>
  <Dialog
    :visible="visible"
    modal
    :header="dialogTitle"
    :style="{ width: 'min(960px, 96vw)' }"
    @update:visible="emit('update:visible', $event)"
  >
    <div class="uno-grid uno-gap-4">
      <p class="uno-m-0 uno-text-sm uno-text-[#4c6265]">{{ dialogMessage }}</p>

      <DataTable
        :value="historyPage.items"
        size="small"
        data-key="run_id"
        selection-mode="single"
        @row-click="emit('row-open', $event.data)"
      >
        <Column field="date" :header="t('common.date')" />
        <Column field="research_depth" :header="t('analysis.depth')">
          <template #body="{ data }">
            <span>{{ formatResearchDepth(data.research_depth, t) }}</span>
          </template>
        </Column>
        <Column field="status" :header="t('common.status')">
          <template #body="{ data }">
            <Tag :value="String(data.status || t('common.na'))" :severity="signalSeverity(data.status)" />
          </template>
        </Column>
        <Column field="signal" :header="t('common.signal')">
          <template #body="{ data }">
            <Tag :value="String(data.signal || t('common.na'))" :severity="signalSeverity(data.signal)" />
          </template>
        </Column>
      </DataTable>

      <Paginator
        :rows="historyPage.page_size"
        :total-records="historyPage.total_count"
        :first="firstRow"
        template="PrevPageLink CurrentPageReport NextPageLink"
        current-page-report-template="{currentPage}/{totalPages}"
        @page="emit('page-change', Number($event.page || 0) + 1)"
      />
    </div>

    <template #footer>
      <div class="uno-flex uno-justify-end uno-gap-2">
        <Button
          v-if="mode === 'active'"
          data-testid="history-dialog-view"
          :label="t('analysis.viewCurrentRun')"
          @click="emit('confirm')"
        />
        <Button
          v-else
          data-testid="history-dialog-confirm"
          :label="t('analysis.startNewAnalysis')"
          @click="emit('confirm')"
        />
        <Button
          data-testid="history-dialog-close"
          :label="t('common.cancel')"
          severity="secondary"
          @click="emit('update:visible', false)"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import Dialog from 'primevue/dialog';
import Paginator from 'primevue/paginator';
import Tag from 'primevue/tag';
import { computed } from 'vue';

import { useI18n } from '../../i18n';
import type { TickerRunHistoryPage } from '../../pages/tickerHistory';
import { signalSeverity } from '../../utils/format';
import { formatResearchDepth } from '../../utils/researchDepth';

const props = defineProps<{
  visible: boolean;
  mode: 'active' | 'recent-history';
  historyPage: TickerRunHistoryPage;
  loading?: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'confirm'): void;
  (e: 'row-open', run: Record<string, unknown>): void;
  (e: 'page-change', page: number): void;
}>();

const { t } = useI18n();

const dialogTitle = computed(() => (
  props.mode === 'active'
    ? t('analysis.activeRunDialogTitle')
    : t('analysis.recentHistoryDialogTitle')
));

const dialogMessage = computed(() => (
  props.mode === 'active'
    ? t('analysis.activeRunDialogMessage')
    : t('analysis.recentHistoryDialogMessage')
));

const firstRow = computed(() => Math.max(0, (props.historyPage.page - 1) * props.historyPage.page_size));
</script>
