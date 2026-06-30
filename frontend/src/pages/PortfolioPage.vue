<template>
  <section>
    <PageHeader
      :eyebrow="t('portfolio.eyebrow')"
      :title="t('portfolio.title')"
      :description="t('portfolio.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="loadAll" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <MetricGrid :items="metrics" />

    <div class="content-grid">
      <Card>
        <template #title>{{ t('common.watchlist') }}</template>
        <template #content>
          <div class="actions-row">
            <InputText v-model="watchTicker" :placeholder="t('common.ticker')" />
            <Button icon="pi pi-plus" :label="t('common.add')" @click="addWatchlist" />
          </div>
          <div class="list-stack" style="margin-top: 0.75rem;">
            <div v-for="item in watchlist" :key="item.ticker" class="list-item">
              <div class="list-item-title">
                <span>{{ item.ticker }}</span>
                <Tag :value="item.latest_signal || item.latest_status || t('common.saved')" :severity="signalSeverity(item.latest_signal || item.latest_status)" />
              </div>
              <small class="muted">{{ item.company_name || item.latest_date || t('portfolio.noSavedRun') }}</small>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('nav.portfolio') }}</template>
        <template #content>
          <div class="form-grid">
            <InputText v-model="position.ticker" :placeholder="t('common.ticker')" />
            <InputText v-model="position.quantity" type="number" :placeholder="t('portfolio.quantity')" />
            <InputText v-model="position.average_cost" type="number" :placeholder="t('portfolio.averageCost')" />
          </div>
          <Button icon="pi pi-plus" :label="t('common.addPosition')" style="margin-top: 0.75rem;" @click="addPosition" />
          <div class="list-stack" style="margin-top: 0.75rem;">
            <div v-for="item in asArray(portfolio?.positions)" :key="item.id" class="list-item">
              <div class="list-item-title">
                <span>{{ item.ticker }} · {{ item.quantity }} @ {{ item.average_cost }}</span>
                <Tag :value="item.latest_signal || t('common.na')" :severity="signalSeverity(item.latest_signal)" />
              </div>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('portfolio.alerts') }}</template>
        <template #content>
          <div class="form-grid">
            <InputText v-model="alertRule.ticker" :placeholder="t('common.ticker')" />
            <Select v-model="alertRule.field" :options="alertFields" option-label="label" option-value="value" />
            <InputText v-model="alertRule.value" :placeholder="t('portfolio.valuePlaceholder')" />
          </div>
          <Button icon="pi pi-bell" :label="t('common.addRule')" style="margin-top: 0.75rem;" @click="addAlert" />
          <div class="list-stack" style="margin-top: 0.75rem;">
            <div v-for="rule in asArray(alerts?.rules)" :key="rule.id" class="list-item">
              <div class="list-item-title">
                <span>{{ rule.ticker }} · {{ rule.field }} = {{ rule.value }}</span>
                <Button icon="pi pi-trash" text severity="danger" :aria-label="t('portfolio.deleteAlert')" @click="deleteAlert(rule.id)" />
              </div>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('portfolio.screener') }}</template>
        <template #content>
          <div class="actions-row">
            <Select v-model="screenerScope" :options="screenerScopes" option-label="label" option-value="value" @change="loadScreener" />
            <InputText v-model="screenerQuery" :placeholder="t('portfolio.searchCandidates')" @input="loadScreener" />
          </div>
          <DataTable :value="asArray(screener?.rows)" size="small" style="margin-top: 0.75rem;">
            <Column field="ticker" :header="t('common.ticker')" />
            <Column field="latest_status" :header="t('common.status')" />
            <Column field="latest_signal" :header="t('common.signal')" />
            <Column field="run_count" :header="t('nav.runs')" />
          </DataTable>
        </template>
      </Card>
    </div>
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
import Tag from 'primevue/tag';
import { computed, onMounted, reactive, ref } from 'vue';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPost } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, signalSeverity, type JsonRecord } from '../utils/format';

const session = useSession();
const watchlist = ref<JsonRecord[]>([]);
const portfolio = ref<JsonRecord | null>(null);
const alerts = ref<JsonRecord | null>(null);
const screener = ref<JsonRecord | null>(null);
const error = ref('');
const watchTicker = ref('');
const screenerScope = ref('all');
const screenerQuery = ref('');
const position = reactive({ ticker: '', quantity: '', average_cost: '' });
const alertRule = reactive({ ticker: '', field: 'signal', value: '' });
const { t } = useI18n();

const alertFields = computed(() => [
  { label: t('common.signal'), value: 'signal' },
  { label: t('common.status'), value: 'status' },
]);
const screenerScopes = computed(() => [
  { label: t('portfolio.scopeAllSaved'), value: 'all' },
  { label: t('common.watchlist'), value: 'watchlist' },
  { label: t('nav.portfolio'), value: 'portfolio' },
  { label: t('portfolio.scopePinned'), value: 'pinned' },
]);
const metrics = computed(() => [
  { label: t('common.watchlist'), value: watchlist.value.length },
  { label: t('portfolio.positions'), value: asArray(portfolio.value?.positions).length },
  { label: t('portfolio.alertRules'), value: asArray(alerts.value?.rules).length },
  { label: t('portfolio.screenerRows'), value: asArray(screener.value?.rows).length },
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

async function loadScreener() {
  const params = new URLSearchParams();
  params.set('scope', screenerScope.value);
  if (screenerQuery.value.trim()) params.set('q', screenerQuery.value.trim());
  screener.value = await apiGet<JsonRecord>(`/api/screener?${params.toString()}`, session.apiContext.value);
}

async function loadAll() {
  error.value = '';
  try {
    await Promise.all([loadWatchlist(), loadPortfolio(), loadAlerts(), loadScreener()]);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('portfolio.loadError');
  }
}

async function addWatchlist() {
  if (!watchTicker.value.trim()) return;
  await apiPost('/api/watchlist', { ticker: watchTicker.value.trim().toUpperCase() }, session.apiContext.value);
  watchTicker.value = '';
  await loadWatchlist();
}

async function addPosition() {
  if (!position.ticker.trim()) return;
  await apiPost('/api/portfolio/positions', {
    ticker: position.ticker.trim().toUpperCase(),
    quantity: Number(position.quantity || 0),
    average_cost: Number(position.average_cost || 0),
  }, session.apiContext.value);
  Object.assign(position, { ticker: '', quantity: '', average_cost: '' });
  await loadPortfolio();
}

async function addAlert() {
  if (!alertRule.ticker.trim() || !alertRule.value.trim()) return;
  await apiPost('/api/alerts/rules', {
    ticker: alertRule.ticker.trim().toUpperCase(),
    field: alertRule.field,
    value: alertRule.value.trim(),
  }, session.apiContext.value);
  Object.assign(alertRule, { ticker: '', field: 'signal', value: '' });
  await loadAlerts();
}

async function deleteAlert(ruleId: string) {
  await apiDelete(`/api/alerts/rules/${encodeURIComponent(ruleId)}`, session.apiContext.value);
  await loadAlerts();
}

onMounted(loadAll);
</script>
