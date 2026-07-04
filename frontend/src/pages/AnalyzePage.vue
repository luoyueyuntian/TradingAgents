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

    <div data-testid="analysis-layout" class="uno-grid uno-gap-4">
      <Card>
        <template #title>{{ t('analysis.configuration') }}</template>
        <template #content>
          <div class="uno-grid uno-gap-4">
            <div
              data-testid="analysis-form-row-primary"
              class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(min(100%,220px),1fr))] uno-gap-[0.8rem]"
            >
              <label class="uno-grid uno-gap-[0.35rem]">
                <span class="uno-text-[#6f8183]">{{ t('analysis.stockMarket') }}</span>
                <Select
                  v-model="form.stock_market"
                  :options="stockMarketOptions"
                  option-label="label"
                  option-value="value"
                  class="uno-w-full"
                  @change="handleStockMarketChange"
                />
              </label>
              <label class="uno-grid uno-gap-[0.35rem]">
                <span class="uno-text-[#6f8183]">{{ t('common.ticker') }}</span>
                <AutoComplete
                  v-model="selectedStock"
                  :suggestions="stockOptions"
                  option-label="label"
                  :placeholder="t('analysis.stockPlaceholder')"
                  :loading="stockLoading"
                  dropdown
                  complete-on-focus
                  force-selection
                  show-clear
                  fluid
                  class="uno-w-full"
                  @complete="onStockComplete"
                  @clear="clearSelectedStock"
                >
                  <template #option="{ option }">
                    <div class="uno-grid uno-min-w-0 uno-gap-0.5">
                      <strong class="uno-truncate uno-text-[#132a2d]">{{ option.symbol }}</strong>
                      <small class="uno-truncate uno-text-[#6f8183]">{{ [option.name, option.exchange].filter(Boolean).join(' · ') }}</small>
                    </div>
                  </template>
                </AutoComplete>
              </label>
              <label class="uno-grid uno-gap-[0.35rem]">
                <span class="uno-text-[#6f8183]">{{ t('analysis.marketProfile') }}</span>
                <Select
                  v-model="form.market_profile"
                  :options="marketProfileOptions"
                  option-label="label"
                  option-value="value"
                  class="uno-w-full"
                  disabled
                />
              </label>
              <label class="uno-grid uno-gap-[0.35rem]">
                <span class="uno-text-[#6f8183]">{{ t('analysis.analysisDate') }}</span>
                <DatePicker
                  v-model="analysisDate"
                  date-format="yy-mm-dd"
                  show-icon
                  icon-display="input"
                  :manual-input="false"
                  fluid
                  input-class="uno-w-full"
                />
              </label>
            </div>

            <div
              data-testid="analysis-form-row-models"
              class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(min(100%,260px),1fr))] uno-gap-[0.8rem]"
            >
              <label class="uno-grid uno-gap-[0.35rem]">
                <span class="uno-text-[#6f8183]">{{ t('common.provider') }}</span>
                <Select
                  v-model="form.llm_provider"
                  :options="providerOptions"
                  option-label="label"
                  option-value="value"
                  :placeholder="t('common.provider')"
                  class="uno-w-full"
                  @change="syncProviderModels"
                />
              </label>
              <label class="uno-grid uno-min-w-0 uno-gap-[0.35rem]">
                <span class="uno-text-[#6f8183]">{{ t('analysis.quickModel') }}</span>
                <Select
                  v-model="form.quick_think_model"
                  :options="quickModelOptions"
                  option-label="label"
                  option-value="value"
                  class="uno-w-full"
                  :pt="modelSelectPt"
                />
              </label>
              <label class="uno-grid uno-min-w-0 uno-gap-[0.35rem]">
                <span class="uno-text-[#6f8183]">{{ t('analysis.deepModel') }}</span>
                <Select
                  v-model="form.deep_think_model"
                  :options="deepModelOptions"
                  option-label="label"
                  option-value="value"
                  class="uno-w-full"
                  :pt="modelSelectPt"
                />
              </label>
              <label class="uno-grid uno-gap-[0.35rem]">
                <span class="uno-text-[#6f8183]">{{ t('analysis.depth') }}</span>
                <Select v-model="form.research_depth" :options="depthOptions" option-label="label" option-value="value" class="uno-w-full" />
              </label>
            </div>

            <div
              data-testid="analysis-form-row-actions"
              class="uno-flex uno-flex-wrap uno-items-end uno-gap-[0.8rem]"
            >
              <label class="uno-grid uno-min-w-[220px] uno-flex-1 uno-gap-[0.35rem]">
                <span class="uno-text-[#6f8183]">{{ t('common.language') }}</span>
                <Select v-model="form.output_language" :options="languageOptions" option-label="label" option-value="value" class="uno-w-full" />
              </label>
              <Button icon="pi pi-play" :label="t('analysis.startAnalysis')" :loading="submitting" :disabled="!canWrite" @click="startRun" />
            </div>

            <details class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3">
              <summary class="uno-cursor-pointer uno-font-700 uno-text-[#243a3d]">{{ t('analysis.advancedOverrides') }}</summary>
              <div class="uno-mt-3 uno-grid uno-grid-cols-[repeat(auto-fit,minmax(min(100%,220px),1fr))] uno-gap-[0.8rem]">
                <label class="uno-grid uno-gap-[0.35rem]">
                  <span class="uno-text-[#6f8183]">{{ t('settings.riskRounds') }}</span>
                  <InputText v-model="form.max_risk_discuss_rounds" type="number" class="uno-w-full" />
                </label>
                <label class="uno-grid uno-gap-[0.35rem]">
                  <span class="uno-text-[#6f8183]">{{ t('settings.maxRecurLimit') }}</span>
                  <InputText v-model="form.max_recur_limit" type="number" class="uno-w-full" />
                </label>
                <label class="uno-grid uno-gap-[0.35rem]">
                  <span class="uno-text-[#6f8183]">{{ t('settings.benchmarkTicker') }}</span>
                  <InputText v-model="form.benchmark_ticker" :placeholder="t('common.auto')" class="uno-w-full" />
                </label>
                <label class="uno-grid uno-gap-[0.35rem]">
                  <span class="uno-text-[#6f8183]">{{ t('settings.temperature') }}</span>
                  <InputText v-model="form.temperature" type="number" :placeholder="t('common.default')" class="uno-w-full" />
                </label>
                <label class="uno-grid uno-gap-[0.35rem]">
                  <span class="uno-text-[#6f8183]">{{ t('settings.backendUrl') }}</span>
                  <InputText v-model="form.backend_url" :placeholder="t('common.providerDefault')" class="uno-w-full" />
                </label>
                <label class="uno-grid uno-gap-[0.35rem]">
                  <span class="uno-text-[#6f8183]">{{ t('settings.googleThinkingLevel') }}</span>
                  <Select v-model="form.google_thinking_level" :options="googleThinkingOptions" option-label="label" option-value="value" class="uno-w-full" />
                </label>
                <label class="uno-grid uno-gap-[0.35rem]">
                  <span class="uno-text-[#6f8183]">{{ t('settings.openaiReasoningEffort') }}</span>
                  <Select v-model="form.openai_reasoning_effort" :options="reasoningEffortOptions" option-label="label" option-value="value" class="uno-w-full" />
                </label>
                <label class="uno-grid uno-gap-[0.35rem]">
                  <span class="uno-text-[#6f8183]">{{ t('settings.anthropicEffort') }}</span>
                  <Select v-model="form.anthropic_effort" :options="reasoningEffortOptions" option-label="label" option-value="value" class="uno-w-full" />
                </label>
                <label class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                  <input v-model="form.checkpoint_enabled" type="checkbox">
                  <span>{{ t('settings.enableCheckpoint') }}</span>
                </label>
              </div>
            </details>
          </div>

          <div class="uno-mt-4 uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('analysis.analysts') }}</span>
            <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
              <label v-for="item in analystOptions" :key="item.value" class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                <input v-model="form.analysts" type="checkbox" :value="item.value">
                <span>{{ item.label }}</span>
              </label>
            </div>
          </div>

        </template>
      </Card>

      <Card>
        <template #title>{{ t('analysis.currentRun') }}</template>
        <template #content>
          <MetricGrid :items="runMetrics" />
          <div class="uno-mb-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
            <Tag v-if="currentRun" :value="currentRun.status" :severity="signalSeverity(currentRun.status)" />
            <Button v-if="currentRun?.run_id" icon="pi pi-times" :label="t('common.cancel')" severity="danger" outlined :disabled="!canWrite" @click="cancelRun" />
          </div>

          <div v-if="agentProgress.length" class="uno-mb-[0.85rem] uno-grid uno-gap-2">
            <div v-for="agent in agentProgress" :key="agent.name" class="uno-flex uno-min-h-[42px] uno-items-center uno-justify-between uno-gap-3 uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-px-[0.7rem] uno-py-[0.55rem]">
              <span class="uno-min-w-0 uno-break-words uno-font-semibold uno-text-[#243a3d]">{{ agent.name }}</span>
              <Tag :value="agent.status" :severity="signalSeverity(agent.status)" />
            </div>
          </div>

          <div v-if="liveReportText" class="uno-mb-[0.85rem] uno-grid uno-gap-[0.65rem]">
            <div class="uno-flex uno-items-center uno-justify-between uno-gap-3">
              <span class="uno-text-[#6f8183]">{{ t('analysis.liveReport') }}</span>
              <Tag v-if="liveState.latestReportSection" :value="sectionLabel(liveState.latestReportSection)" severity="info" />
            </div>
            <ReportMarkdown :content="liveReportText" :empty-text="t('runs.noReport')" />
          </div>

          <details class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3" :open="!liveReportText && !agentProgress.length">
            <summary class="uno-cursor-pointer uno-font-700 uno-text-[#243a3d]">{{ t('analysis.terminalOutput') }}</summary>
            <pre class="uno-m-0 uno-mt-3 uno-max-h-[520px] uno-overflow-auto uno-whitespace-pre-wrap uno-break-words uno-rounded-lg uno-bg-[#101b1d] uno-p-[0.85rem] uno-text-[#d8f3ee]">{{ logText || t('analysis.noActiveRun') }}</pre>
          </details>
        </template>
      </Card>
    </div>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import AutoComplete from 'primevue/autocomplete';
import DatePicker from 'primevue/datepicker';
import Message from 'primevue/message';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue';
import { useRouter } from 'vue-router';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import ReportMarkdown from '../components/ReportMarkdown.vue';
import { useI18n } from '../i18n';
import { apiGet, apiPost } from '../services/api';
import { useSession } from '../stores/session';
import { signalSeverity, type JsonRecord } from '../utils/format';
import { createLiveRunViewState, type LiveRunViewState } from '../utils/runDisplay';
import {
  buildAnalysisRequestPayload,
  buildStockSearchPath,
  formatAnalysisDate,
  marketProfileForStockMarket,
  normalizeStockOptions,
  parseAnalysisDate,
  type StockCatalogOption,
  type StockMarketOption,
} from './analyzeStockSelection';

const router = useRouter();
const session = useSession();
const canWrite = computed(() => session.canWrite.value);
const providers = ref<JsonRecord[]>([]);
const stockMarkets = ref<StockMarketOption[]>([]);
const stocks = ref<Required<StockCatalogOption>[]>([]);
const selectedStock = ref<Required<StockCatalogOption> | string | null>(null);
const currentRun = ref<JsonRecord | null>(null);
const error = ref('');
const notice = ref('');
const submitting = ref(false);
const stockLoading = ref(false);
const liveState = ref<LiveRunViewState>(createLiveRunViewState());
const lastStockQuery = ref('');
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
  max_risk_discuss_rounds: '1',
  max_recur_limit: '100',
  checkpoint_enabled: false,
  benchmark_ticker: '',
  backend_url: '',
  temperature: '',
  google_thinking_level: '',
  openai_reasoning_effort: '',
  anthropic_effort: '',
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
const googleThinkingOptions = computed(() => [
  { label: t('common.default'), value: '' },
  { label: t('settings.effortHigh'), value: 'high' },
  { label: t('settings.effortMedium'), value: 'medium' },
  { label: t('settings.effortLow'), value: 'low' },
  { label: t('settings.effortMinimal'), value: 'minimal' },
]);
const reasoningEffortOptions = computed(() => [
  { label: t('common.default'), value: '' },
  { label: t('settings.effortHigh'), value: 'high' },
  { label: t('settings.effortMedium'), value: 'medium' },
  { label: t('settings.effortLow'), value: 'low' },
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
const modelSelectPt = {
  label: { class: 'uno-block uno-max-w-full uno-overflow-hidden uno-text-ellipsis uno-whitespace-nowrap' },
  optionLabel: { class: 'uno-block uno-max-w-full uno-overflow-hidden uno-text-ellipsis uno-whitespace-nowrap' },
};

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
const analysisDate = computed<Date | null>({
  get: () => parseAnalysisDate(form.date),
  set: (value) => {
    form.date = formatAnalysisDate(value) || today;
  },
});

function syncProviderModels() {
  const provider = selectedProvider.value;
  if (!form.quick_think_model) {
    form.quick_think_model = provider?.quick_models?.[0]?.value || '';
  }
  if (!form.deep_think_model) {
    form.deep_think_model = provider?.deep_models?.[0]?.value || '';
  }
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

async function loadSettingsDefaults() {
  try {
    const settings = await apiGet<JsonRecord>('/api/settings', session.apiContext.value);
    const llm = settings.llm || {};
    const analysis = settings.analysis || {};
    const configuredMarketProfile = String(analysis.market_profile || form.market_profile);
    form.llm_provider = String(llm.provider || form.llm_provider);
    form.quick_think_model = String(llm.quick_think_model || form.quick_think_model);
    form.deep_think_model = String(llm.deep_think_model || form.deep_think_model);
    form.output_language = String(analysis.output_language || form.output_language);
    form.stock_market = configuredMarketProfile === 'cn_a' ? 'cn_a' : form.stock_market;
    form.market_profile = marketProfileForStockMarket(form.stock_market);
    form.research_depth = Number(analysis.research_depth || form.research_depth);
    form.max_risk_discuss_rounds = String(analysis.max_risk_discuss_rounds ?? form.max_risk_discuss_rounds);
    form.max_recur_limit = String(analysis.max_recur_limit ?? form.max_recur_limit);
    form.checkpoint_enabled = Boolean(analysis.checkpoint_enabled);
    form.benchmark_ticker = String(analysis.benchmark_ticker || '');
    form.backend_url = String(llm.backend_url || '');
    form.temperature = llm.temperature === null || llm.temperature === undefined ? '' : String(llm.temperature);
    form.google_thinking_level = String(llm.google_thinking_level || '');
    form.openai_reasoning_effort = String(llm.openai_reasoning_effort || '');
    form.anthropic_effort = String(llm.anthropic_effort || '');
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('settings.loadError');
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
  lastStockQuery.value = query;
  stockLoading.value = true;
  try {
    const rows = await apiGet<StockCatalogOption[]>(
      buildStockSearchPath(form.stock_market, query, 100),
      session.apiContext.value,
    );
    stocks.value = normalizeStockOptions(rows);
    if (form.ticker) {
      const exactMatch = stocks.value.find((item) => item.symbol === form.ticker);
      if (exactMatch) {
        selectedStock.value = exactMatch;
      }
    }
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
  selectedStock.value = null;
  lastStockQuery.value = '';
  await loadStocks();
}

async function onStockComplete(event: { query?: string }) {
  await loadStocks(event.query || '');
}

function clearSelectedStock() {
  selectedStock.value = null;
  form.ticker = '';
}

async function handleExternalStockCatalogRefresh() {
  error.value = '';
  notice.value = t('analysis.stocksRefreshed');
  await loadStocks(lastStockQuery.value);
}

function handleExternalStockCatalogRefreshFailure(event: Event) {
  notice.value = '';
  error.value = event instanceof CustomEvent && typeof event.detail === 'string' && event.detail
    ? event.detail
    : t('analysis.stocksLoadError');
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
    liveState.value = {
      ...createLiveRunViewState(),
      status: String(currentRun.value.status || 'queued'),
      logLines: [t('analysis.runCreated', { runId: String(currentRun.value.run_id) })],
    };
    await router.push({
      name: 'runs',
      query: {
        market: form.stock_market,
        ticker: form.ticker,
      },
    });
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('analysis.startError');
  } finally {
    submitting.value = false;
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
  await Promise.all([loadProviders(), loadStockMarkets(), loadSettingsDefaults()]);
  await loadStocks();
}

watch(selectedStock, (value) => {
  if (!value) {
    form.ticker = '';
    return;
  }
  if (typeof value === 'object') {
    form.ticker = value.symbol;
  }
});

onMounted(() => {
  window.addEventListener('tradingagents:stock-catalog-refreshed', handleExternalStockCatalogRefresh);
  window.addEventListener('tradingagents:stock-catalog-refresh-failed', handleExternalStockCatalogRefreshFailure);
  void loadInitialData();
});
onBeforeUnmount(() => {
  window.removeEventListener('tradingagents:stock-catalog-refreshed', handleExternalStockCatalogRefresh);
  window.removeEventListener('tradingagents:stock-catalog-refresh-failed', handleExternalStockCatalogRefreshFailure);
});

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
