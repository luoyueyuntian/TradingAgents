<template>
  <section>
    <PageHeader
      :eyebrow="t('analysis.eyebrow')"
      :title="t('analysis.title')"
      :description="t('analysis.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('analysis.reloadModels')" severity="secondary" @click="loadProviders" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Message v-if="notice" severity="success" :closable="false">{{ notice }}</Message>

    <div class="content-grid">
      <Card>
        <template #title>{{ t('analysis.configuration') }}</template>
        <template #content>
          <div class="form-grid">
            <label class="field">
              <span class="field-label">{{ t('analysis.stockMarket') }}</span>
              <Select
                v-model="form.stock_market"
                :options="stockMarketOptions"
                option-label="label"
                option-value="value"
                @change="handleStockMarketChange"
              />
            </label>
            <label class="field">
              <span class="field-label">{{ t('common.ticker') }}</span>
              <Select
                v-model="form.ticker"
                :options="stockOptions"
                option-label="label"
                option-value="symbol"
                :placeholder="t('analysis.stockPlaceholder')"
                :loading="stockLoading"
                filter
                show-clear
                @filter="onStockFilter"
              />
            </label>
            <div class="field">
              <span class="field-label">{{ t('analysis.stockCatalog') }}</span>
              <Button
                icon="pi pi-sync"
                :label="t('analysis.refreshStocks')"
                severity="secondary"
                :loading="refreshingStocks"
                @click="refreshStockCatalog"
              />
            </div>
            <label class="field">
              <span class="field-label">{{ t('analysis.analysisDate') }}</span>
              <InputText v-model="form.date" type="date" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('common.provider') }}</span>
              <Select
                v-model="form.llm_provider"
                :options="providerOptions"
                option-label="label"
                option-value="value"
                :placeholder="t('common.provider')"
                @change="syncProviderModels"
              />
            </label>
            <label class="field">
              <span class="field-label">{{ t('analysis.quickModel') }}</span>
              <Select v-model="form.quick_think_model" :options="quickModelOptions" option-label="label" option-value="value" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('analysis.deepModel') }}</span>
              <Select v-model="form.deep_think_model" :options="deepModelOptions" option-label="label" option-value="value" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('analysis.depth') }}</span>
              <Select v-model="form.research_depth" :options="depthOptions" option-label="label" option-value="value" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('common.language') }}</span>
              <Select v-model="form.output_language" :options="languageOptions" option-label="label" option-value="value" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('analysis.marketProfile') }}</span>
              <Select
                v-model="form.market_profile"
                :options="marketProfileOptions"
                option-label="label"
                option-value="value"
                disabled
              />
            </label>
          </div>

          <div class="field" style="margin-top: 1rem;">
            <span class="field-label">{{ t('analysis.analysts') }}</span>
            <div class="actions-row">
              <label v-for="item in analystOptions" :key="item.value" class="inline-row">
                <input v-model="form.analysts" type="checkbox" :value="item.value">
                <span>{{ item.label }}</span>
              </label>
            </div>
          </div>

          <div class="actions-row" style="margin-top: 1rem;">
            <Button icon="pi pi-play" :label="t('analysis.startAnalysis')" :loading="submitting" @click="startRun" />
            <Button icon="pi pi-list" :label="t('analysis.openRuns')" severity="secondary" @click="$router.push('/runs')" />
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('analysis.currentRun') }}</template>
        <template #content>
          <MetricGrid :items="runMetrics" />
          <div class="actions-row" style="margin-bottom: 0.75rem;">
            <Tag v-if="currentRun" :value="currentRun.status" :severity="signalSeverity(currentRun.status)" />
            <Button v-if="currentRun?.run_id" icon="pi pi-times" :label="t('common.cancel')" severity="danger" outlined @click="cancelRun" />
          </div>

          <div v-if="agentProgress.length" class="agent-progress-grid">
            <div v-for="agent in agentProgress" :key="agent.name" class="agent-progress-item">
              <span>{{ agent.name }}</span>
              <Tag :value="agent.status" :severity="signalSeverity(agent.status)" />
            </div>
          </div>

          <div v-if="liveReportText" class="live-report-panel">
            <div class="live-report-header">
              <span class="field-label">{{ t('analysis.liveReport') }}</span>
              <Tag v-if="liveState.latestReportSection" :value="sectionLabel(liveState.latestReportSection)" severity="info" />
            </div>
            <ReportMarkdown :content="liveReportText" :empty-text="t('runs.noReport')" />
          </div>

          <details class="event-log-panel" :open="!liveReportText && !agentProgress.length">
            <summary>{{ t('analysis.eventLog') }}</summary>
            <pre class="log-box">{{ logText || t('analysis.noActiveRun') }}</pre>
          </details>
        </template>
      </Card>
    </div>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import ReportMarkdown from '../components/ReportMarkdown.vue';
import { useI18n } from '../i18n';
import { apiGet, apiPost, buildApiUrl } from '../services/api';
import { useSession } from '../stores/session';
import { signalSeverity, type JsonRecord } from '../utils/format';
import { applyRunStreamEvent, createLiveRunViewState, type LiveRunViewState } from '../utils/runDisplay';
import {
  buildAnalysisRequestPayload,
  buildStockSearchPath,
  marketProfileForStockMarket,
  normalizeStockOptions,
  type StockCatalogOption,
  type StockMarketOption,
} from './analyzeStockSelection';

const session = useSession();
const providers = ref<JsonRecord[]>([]);
const stockMarkets = ref<StockMarketOption[]>([]);
const stocks = ref<Required<StockCatalogOption>[]>([]);
const currentRun = ref<JsonRecord | null>(null);
const error = ref('');
const notice = ref('');
const submitting = ref(false);
const stockLoading = ref(false);
const refreshingStocks = ref(false);
const liveState = ref<LiveRunViewState>(createLiveRunViewState());
let eventSource: EventSource | null = null;
const { t } = useI18n();

const today = new Date().toISOString().slice(0, 10);
const form = reactive({
  stock_market: 'us',
  ticker: '',
  date: today,
  llm_provider: 'openai',
  quick_think_model: '',
  deep_think_model: '',
  research_depth: 3,
  output_language: 'English',
  market_profile: 'default',
  analysts: ['market', 'social', 'news', 'fundamentals'],
});

const analystOptions = computed(() => [
  { label: t('analysis.analystMarket'), value: 'market' },
  { label: t('analysis.analystSentiment'), value: 'social' },
  { label: t('analysis.analystNews'), value: 'news' },
  { label: t('analysis.analystFundamentals'), value: 'fundamentals' },
]);
const depthOptions = computed(() => [
  { label: t('analysis.depthShallow'), value: 1 },
  { label: t('analysis.depthMedium'), value: 3 },
  { label: t('analysis.depthDeep'), value: 5 },
]);
const languageOptions = computed(() => [
  { label: t('analysis.languageEnglish'), value: 'English' },
  { label: t('analysis.languageChinese'), value: 'Chinese' },
  { label: t('analysis.languageJapanese'), value: 'Japanese' },
  { label: t('analysis.languageKorean'), value: 'Korean' },
  { label: t('analysis.languageSpanish'), value: 'Spanish' },
  { label: t('analysis.languageFrench'), value: 'French' },
  { label: t('analysis.languageGerman'), value: 'German' },
]);
const marketProfileOptions = computed(() => [
  { label: t('analysis.marketDefault'), value: 'default' },
  { label: t('analysis.marketChinaA'), value: 'cn_a' },
]);
const fallbackStockMarketOptions = computed(() => [
  { label: t('analysis.usStocks'), value: 'us' },
  { label: t('analysis.hkStocks'), value: 'hk' },
  { label: t('analysis.cnAStocks'), value: 'cn_a' },
]);
const stockMarketOptions = computed(() => (
  stockMarkets.value.length ? stockMarkets.value : fallbackStockMarketOptions.value
).map((option) => ({
  ...option,
  label: stockMarketLabel(option.value, option.label),
})));
const stockOptions = computed(() => stocks.value);

const providerOptions = computed(() => providers.value.map((provider) => ({
  label: provider.display_name || provider.provider,
  value: provider.provider,
})));
const selectedProvider = computed(() => providers.value.find((provider) => provider.provider === form.llm_provider));
const quickModelOptions = computed(() => selectedProvider.value?.quick_models || []);
const deepModelOptions = computed(() => selectedProvider.value?.deep_models || []);
const logText = computed(() => liveState.value.logLines.join('\n'));
const liveReportText = computed(() => liveState.value.terminalReport || liveState.value.currentReport);
const agentProgress = computed(() => Object.entries(liveState.value.agents).map(([name, status]) => ({ name, status })));
const runMetrics = computed(() => [
  { label: t('common.runId'), value: currentRun.value?.run_id || t('common.na') },
  { label: t('common.ticker'), value: currentRun.value?.ticker || form.ticker || t('common.na') },
  { label: t('common.status'), value: liveState.value.status || currentRun.value?.status || t('common.idle') },
  { label: t('common.signal'), value: liveState.value.signal || currentRun.value?.signal || t('common.pending') },
]);

function syncProviderModels() {
  const provider = selectedProvider.value;
  form.quick_think_model = provider?.quick_models?.[0]?.value || '';
  form.deep_think_model = provider?.deep_models?.[0]?.value || '';
}

async function loadProviders() {
  error.value = '';
  try {
    providers.value = await apiGet<JsonRecord[]>('/api/providers', session.apiContext.value);
    if (!selectedProvider.value && providers.value.length) {
      form.llm_provider = String(providers.value[0].provider);
    }
    syncProviderModels();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('analysis.providersLoadError');
  }
}

async function loadStockMarkets() {
  try {
    stockMarkets.value = await apiGet<StockMarketOption[]>('/api/stocks/markets', session.apiContext.value);
    if (!stockMarketOptions.value.some((option) => option.value === form.stock_market)) {
      form.stock_market = stockMarketOptions.value[0]?.value || 'us';
      form.market_profile = marketProfileForStockMarket(form.stock_market);
    }
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('analysis.stocksLoadError');
  }
}

async function loadStocks(query = '') {
  stockLoading.value = true;
  try {
    const rows = await apiGet<StockCatalogOption[]>(
      buildStockSearchPath(form.stock_market, query, 100),
      session.apiContext.value,
    );
    stocks.value = normalizeStockOptions(rows);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('analysis.stocksLoadError');
  } finally {
    stockLoading.value = false;
  }
}

async function handleStockMarketChange() {
  form.ticker = '';
  form.market_profile = marketProfileForStockMarket(form.stock_market);
  stocks.value = [];
  await loadStocks();
}

async function onStockFilter(event: { value?: string }) {
  await loadStocks(event.value || '');
}

async function refreshStockCatalog() {
  error.value = '';
  notice.value = '';
  refreshingStocks.value = true;
  try {
    await apiPost<JsonRecord>('/api/stocks/refresh', { force: true }, session.apiContext.value);
    notice.value = t('analysis.stocksRefreshed');
    await loadStocks();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('analysis.stocksLoadError');
  } finally {
    refreshingStocks.value = false;
  }
}

function buildRequest() {
  return buildAnalysisRequestPayload(form);
}

async function startRun() {
  error.value = '';
  notice.value = '';
  if (!form.ticker.trim()) {
    error.value = t('analysis.tickerRequired');
    return;
  }
  submitting.value = true;
  try {
    currentRun.value = await apiPost<JsonRecord>('/api/runs', buildRequest(), session.apiContext.value);
    notice.value = t('analysis.queuedNotice', { ticker: String(currentRun.value.ticker) });
    liveState.value = {
      ...createLiveRunViewState(),
      status: String(currentRun.value.status || 'queued'),
      logLines: [t('analysis.runCreated', { runId: String(currentRun.value.run_id) })],
    };
    startEvents(String(currentRun.value.run_id));
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('analysis.startError');
  } finally {
    submitting.value = false;
  }
}

function startEvents(runId: string) {
  eventSource?.close();
  const url = buildApiUrl(`/api/runs/${encodeURIComponent(runId)}/events`, session.apiContext.value);
  eventSource = new EventSource(url);
  for (const name of ['queued', 'progress', 'agent_status', 'report_update', 'complete', 'cancelled', 'error']) {
    eventSource.addEventListener(name, (event) => {
      const payload = 'data' in event ? String((event as MessageEvent).data || '') : '';
      liveState.value = applyRunStreamEvent(
        liveState.value,
        name,
        payload,
        new Date().toLocaleTimeString(),
      );
      if (currentRun.value && liveState.value.status) {
        currentRun.value = {
          ...currentRun.value,
          status: liveState.value.status,
          signal: liveState.value.signal || currentRun.value.signal,
        };
      }
      if (name === 'complete' || name === 'cancelled' || name === 'error') {
        eventSource?.close();
      }
    });
  }
}

async function cancelRun() {
  if (!currentRun.value?.run_id) {
    return;
  }
  currentRun.value = await apiPost<JsonRecord>(
    `/api/runs/${encodeURIComponent(String(currentRun.value.run_id))}/cancel`,
    {},
    session.apiContext.value,
  );
  liveState.value = {
    ...liveState.value,
    status: String(currentRun.value.status || liveState.value.status),
    logLines: [...liveState.value.logLines, t('analysis.cancelRequested')],
  };
}

async function loadInitialData() {
  await Promise.all([loadProviders(), loadStockMarkets()]);
  await loadStocks();
}

onMounted(loadInitialData);
onBeforeUnmount(() => eventSource?.close());

function stockMarketLabel(value: string, fallback: string): string {
  switch (value) {
    case 'us':
      return t('analysis.usStocks');
    case 'hk':
      return t('analysis.hkStocks');
    case 'cn_a':
      return t('analysis.cnAStocks');
    default:
      return fallback;
  }
}

function sectionLabel(key: string): string {
  switch (key) {
    case 'market_report':
      return t('runs.section.market');
    case 'sentiment_report':
      return t('runs.section.sentiment');
    case 'news_report':
      return t('runs.section.news');
    case 'fundamentals_report':
      return t('runs.section.fundamentals');
    case 'investment_plan':
      return t('runs.section.research');
    case 'trader_investment_plan':
      return t('runs.section.trading');
    case 'final_trade_decision':
      return t('runs.section.decision');
    default:
      return key.replaceAll('_', ' ');
  }
}
</script>
