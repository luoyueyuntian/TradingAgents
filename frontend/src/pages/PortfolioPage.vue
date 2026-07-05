<template>
  <section>
    <PageHeader
      :eyebrow="t('portfolio.eyebrow')"
      :title="t('portfolio.title')"
      :description="t('portfolio.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" :disabled="!canWrite" @click="loadAll" />
      </template>
    </PageHeader>

    <PortfolioSubnav />
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <MetricGrid :items="metrics" />

    <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(220px,1fr))] uno-gap-4">
      <RouterLink
        v-for="section in sections"
        :key="section.to"
        :to="section.to"
        class="uno-rounded-xl uno-border uno-border-[#dce7e7] uno-bg-white uno-p-4 uno-no-underline"
      >
        <div class="uno-text-sm uno-font-700 uno-uppercase uno-tracking-[0.12em] uno-text-[#5f7376]">{{ section.label }}</div>
        <div class="uno-mt-2 uno-text-2xl uno-font-800 uno-text-[#14363a]">{{ section.count }}</div>
      </RouterLink>
    </div>

    <Card class="uno-mt-4">
      <template #title>{{ t('portfolio.screener') }}</template>
      <template #content>
        <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
          <Select v-model="screenerScope" :options="screenerScopes" option-label="label" option-value="value" @change="loadScreener" />
          <InputText v-model="screenerQuery" :placeholder="t('portfolio.searchCandidates')" @input="loadScreener" />
        </div>
        <DataTable :value="asArray(screener?.rows)" size="small" class="uno-mt-3">
          <Column field="ticker" :header="t('common.ticker')" />
          <Column field="latest_status" :header="t('common.status')" />
          <Column field="latest_signal" :header="t('common.signal')" />
          <Column field="run_count" :header="t('nav.runs')" />
        </DataTable>
      </template>
    </Card>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Select from 'primevue/select';
import { computed, onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import PortfolioSubnav from '../components/portfolio/PortfolioSubnav.vue';
import { useI18n } from '../i18n';
import { apiGet } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, type JsonRecord } from '../utils/format';

const session = useSession();
const canWrite = computed(() => session.canWrite.value);
const { t } = useI18n();
const watchlist = ref<JsonRecord[]>([]);
const portfolio = ref<JsonRecord | null>(null);
const alerts = ref<JsonRecord | null>(null);
const screener = ref<JsonRecord | null>(null);
const stockGroups = ref<JsonRecord[]>([]);
const error = ref('');
const screenerScope = ref('all');
const screenerQuery = ref('');

const screenerScopes = computed(() => [
  { label: t('portfolio.scopeAllSaved'), value: 'all' },
  { label: t('common.watchlist'), value: 'watchlist' },
  { label: t('nav.portfolio'), value: 'portfolio' },
  { label: t('portfolio.scopePinned'), value: 'pinned' },
]);

const metrics = computed(() => [
  { label: t('common.watchlist'), value: watchlist.value.length },
  { label: t('portfolio.positions'), value: asArray(portfolio.value?.positions).length },
  { label: t('portfolio.stockGroups'), value: stockGroups.value.length },
  { label: t('portfolio.alertRules'), value: asArray(alerts.value?.rules).length },
]);

const sections = computed(() => [
  { to: '/portfolio/watchlist', label: t('portfolio.watchlistTitle'), count: watchlist.value.length },
  { to: '/portfolio/positions', label: t('portfolio.positionsTitle'), count: asArray(portfolio.value?.positions).length },
  { to: '/portfolio/stock-groups', label: t('portfolio.stockGroupsTitle'), count: stockGroups.value.length },
  { to: '/portfolio/alerts', label: t('portfolio.alertsTitle'), count: asArray(alerts.value?.rules).length },
]);

async function loadWatchlist() {
  watchlist.value = await apiGet<JsonRecord[]>('/api/watchlist', session.apiContext.value);
}

async function loadPortfolio() {
  portfolio.value = await apiGet<JsonRecord>('/api/portfolio', session.apiContext.value);
}

async function loadAlerts() {
  alerts.value = await apiGet<JsonRecord>('/api/alerts', session.apiContext.value);
}

async function loadStockGroups() {
  stockGroups.value = await apiGet<JsonRecord[]>('/api/stock-groups', session.apiContext.value);
}

async function loadScreener() {
  const params = new URLSearchParams();
  params.set('scope', screenerScope.value);
  if (screenerQuery.value.trim()) {
    params.set('q', screenerQuery.value.trim());
  }
  screener.value = await apiGet<JsonRecord>(`/api/screener?${params.toString()}`, session.apiContext.value);
}

async function loadAll() {
  error.value = '';
  try {
    await Promise.all([loadWatchlist(), loadPortfolio(), loadAlerts(), loadStockGroups(), loadScreener()]);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('portfolio.loadError');
  }
}

onMounted(loadAll);
</script>
