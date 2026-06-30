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
              <span class="field-label">{{ t('common.ticker') }}</span>
              <InputText v-model="form.ticker" placeholder="NVDA, 0700.HK, BTC-USD" />
            </label>
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
              <Select v-model="form.market_profile" :options="marketProfileOptions" option-label="label" option-value="value" />
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
          <pre class="log-box">{{ logText || t('analysis.noActiveRun') }}</pre>
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
import { useI18n } from '../i18n';
import { apiGet, apiPost, buildApiUrl } from '../services/api';
import { useSession } from '../stores/session';
import { signalSeverity, type JsonRecord } from '../utils/format';

const session = useSession();
const providers = ref<JsonRecord[]>([]);
const currentRun = ref<JsonRecord | null>(null);
const error = ref('');
const notice = ref('');
const submitting = ref(false);
const logLines = ref<string[]>([]);
let eventSource: EventSource | null = null;
const { t } = useI18n();

const today = new Date().toISOString().slice(0, 10);
const form = reactive({
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

const providerOptions = computed(() => providers.value.map((provider) => ({
  label: provider.display_name || provider.provider,
  value: provider.provider,
})));
const selectedProvider = computed(() => providers.value.find((provider) => provider.provider === form.llm_provider));
const quickModelOptions = computed(() => selectedProvider.value?.quick_models || []);
const deepModelOptions = computed(() => selectedProvider.value?.deep_models || []);
const logText = computed(() => logLines.value.join('\n'));
const runMetrics = computed(() => [
  { label: t('common.runId'), value: currentRun.value?.run_id || t('common.na') },
  { label: t('common.ticker'), value: currentRun.value?.ticker || form.ticker || t('common.na') },
  { label: t('common.status'), value: currentRun.value?.status || t('common.idle') },
  { label: t('common.signal'), value: currentRun.value?.signal || t('common.pending') },
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

function buildRequest() {
  return {
    ticker: form.ticker.trim().toUpperCase(),
    date: form.date,
    analysts: form.analysts,
    llm_provider: form.llm_provider,
    quick_think_model: form.quick_think_model,
    deep_think_model: form.deep_think_model,
    research_depth: form.research_depth,
    output_language: form.output_language,
    market_profile: form.market_profile,
  };
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
    logLines.value = [t('analysis.runCreated', { runId: String(currentRun.value.run_id) })];
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
      logLines.value.push(`${new Date().toLocaleTimeString()} ${name}: ${payload}`);
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
  logLines.value.push(t('analysis.cancelRequested'));
}

onMounted(loadProviders);
onBeforeUnmount(() => eventSource?.close());
</script>
