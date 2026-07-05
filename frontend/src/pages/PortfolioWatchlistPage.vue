<template>
  <section>
    <PageHeader
      :eyebrow="t('portfolio.eyebrow')"
      :title="t('portfolio.watchlistTitle')"
      :description="t('portfolio.watchlistDescription')"
    >
      <template #actions>
        <Button icon="pi pi-plus" :label="t('common.add')" :disabled="!canWrite" @click="dialogOpen = true" />
      </template>
    </PageHeader>

    <PortfolioSubnav />
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <MetricGrid :items="metrics" />

    <DataTable :value="rows" size="small" class="uno-rounded-xl uno-border uno-border-[#dce7e7] uno-bg-white">
      <Column field="ticker" :header="t('common.ticker')" />
      <Column field="company_name" :header="t('common.companyName')">
        <template #body="{ data }">
          {{ data.company_name || t('common.na') }}
        </template>
      </Column>
      <Column field="run_count" :header="t('portfolio.runCount')" />
      <Column field="latest_run_id" :header="t('portfolio.latestRunId')" />
      <Column :header="t('common.signal')">
        <template #body="{ data }">
          <Tag :value="data.latest_signal || t('common.na')" :severity="signalSeverity(data.latest_signal)" />
        </template>
      </Column>
      <Column :header="t('common.status')">
        <template #body="{ data }">
          <Tag :value="data.latest_status || t('common.na')" :severity="signalSeverity(data.latest_status)" />
        </template>
      </Column>
      <Column field="latest_date" :header="t('common.date')">
        <template #body="{ data }">
          {{ data.latest_date || t('portfolio.noSavedRun') }}
        </template>
      </Column>
      <Column :header="t('common.created')">
        <template #body="{ data }">
          {{ formatDateTime(data.created_at) }}
        </template>
      </Column>
      <Column v-if="canWrite" :header="t('common.actions')">
        <template #body="{ data }">
          <Button
            :data-testid="`watchlist-delete-${data.ticker}`"
            icon="pi pi-trash"
            severity="danger"
            text
            @click="removeTicker(data.ticker)"
          />
        </template>
      </Column>
    </DataTable>

    <WatchlistCreateDialog v-model:visible="dialogOpen" @saved="loadRows" />
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import Message from 'primevue/message';
import Tag from 'primevue/tag';
import { computed, onMounted, ref } from 'vue';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import PortfolioSubnav from '../components/portfolio/PortfolioSubnav.vue';
import WatchlistCreateDialog from '../components/portfolio/WatchlistCreateDialog.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet } from '../services/api';
import { useSession } from '../stores/session';
import { formatDateTime, signalSeverity, type JsonRecord } from '../utils/format';

const session = useSession();
const canWrite = computed(() => session.canWrite.value);
const { t } = useI18n();
const rows = ref<JsonRecord[]>([]);
const error = ref('');
const dialogOpen = ref(false);

const metrics = computed(() => [
  { label: t('common.watchlist'), value: rows.value.length },
]);

async function loadRows() {
  error.value = '';
  try {
    rows.value = await apiGet<JsonRecord[]>('/api/watchlist', session.apiContext.value);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('portfolio.loadError');
  }
}

async function removeTicker(ticker: string) {
  await apiDelete(`/api/watchlist/${encodeURIComponent(ticker)}`, session.apiContext.value);
  await loadRows();
}

onMounted(loadRows);
</script>
