<template>
  <section>
    <PageHeader
      :eyebrow="t('automations.eyebrow')"
      :title="t('automations.title')"
      :description="t('automations.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="loadRules" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div data-testid="automation-layout" class="uno-grid uno-gap-4">
      <Card>
        <template #title>{{ t('automations.createRule') }}</template>
        <template #content>
          <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(220px,1fr))] uno-gap-[0.8rem]">
            <InputText v-model="form.name" :placeholder="t('automations.namePlaceholder')" :disabled="!canWrite" />
            <Select v-model="form.source" :options="sourceOptions" option-label="label" option-value="value" :disabled="!canWrite" />
            <Select v-model="form.cadence" :options="cadenceOptions" option-label="label" option-value="value" :disabled="!canWrite" />
            <Select v-model="form.weekday" :options="weekdayOptions" option-label="label" option-value="value" :disabled="!canWrite || form.cadence !== 'weekly'" />
            <InputText v-model="form.time" type="time" :disabled="!canWrite" />
          </div>
          <Textarea
            v-model="form.tickers"
            rows="3"
            auto-resize
            :placeholder="t('automations.manualTickersPlaceholder')"
            class="uno-mt-3 uno-w-full"
            :disabled="!canWrite"
          />
          <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
            <label class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
              <input v-model="form.enabled" type="checkbox" :disabled="!canWrite">
              <span>{{ t('common.enabled') }}</span>
            </label>
            <Button icon="pi pi-save" :label="t('automations.saveAutomation')" :disabled="!canWrite" @click="saveRule" />
          </div>
          <details class="uno-mt-3 uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3">
            <summary class="uno-cursor-pointer uno-font-700 uno-text-[#243a3d]">{{ t('automations.analysisConfig') }}</summary>
            <div class="uno-mt-3 uno-grid uno-grid-cols-[repeat(auto-fit,minmax(220px,1fr))] uno-gap-[0.8rem]">
              <Select v-model="form.llm_provider" :options="providerOptions" option-label="label" option-value="value" :disabled="!canWrite" @change="syncProviderModels" />
              <InputText v-model="form.quick_think_model" :placeholder="t('analysis.quickModel')" :disabled="!canWrite" />
              <InputText v-model="form.deep_think_model" :placeholder="t('analysis.deepModel')" :disabled="!canWrite" />
              <Select v-model="form.research_depth" :options="depthOptions" option-label="label" option-value="value" :disabled="!canWrite" />
              <Select v-model="form.output_language" :options="languageOptions" option-label="label" option-value="value" :disabled="!canWrite" />
              <Select v-model="form.market_profile" :options="marketProfileOptions" option-label="label" option-value="value" :disabled="!canWrite" />
              <InputText v-model="form.max_risk_discuss_rounds" type="number" :placeholder="t('settings.riskRounds')" :disabled="!canWrite" />
              <InputText v-model="form.max_recur_limit" type="number" :placeholder="t('settings.maxRecurLimit')" :disabled="!canWrite" />
              <InputText v-model="form.benchmark_ticker" :placeholder="t('settings.benchmarkTicker')" :disabled="!canWrite" />
              <InputText v-model="form.backend_url" :placeholder="t('settings.backendUrl')" :disabled="!canWrite" />
              <InputText v-model="form.temperature" type="number" :placeholder="t('settings.temperature')" :disabled="!canWrite" />
              <Select v-model="form.google_thinking_level" :options="googleThinkingOptions" option-label="label" option-value="value" :disabled="!canWrite" />
              <Select v-model="form.openai_reasoning_effort" :options="reasoningEffortOptions" option-label="label" option-value="value" :disabled="!canWrite" />
              <Select v-model="form.anthropic_effort" :options="reasoningEffortOptions" option-label="label" option-value="value" :disabled="!canWrite" />
              <label class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                <input v-model="form.checkpoint_enabled" type="checkbox" :disabled="!canWrite">
                <span>{{ t('settings.enableCheckpoint') }}</span>
              </label>
            </div>
          </details>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('automations.rules') }}</template>
        <template #content>
          <div class="uno-grid uno-gap-[0.65rem]">
            <div v-for="rule in rules" :key="rule.id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ rule.name }}</span>
                <Tag :value="rule.enabled ? t('common.enabled') : t('common.paused')" :severity="rule.enabled ? 'success' : 'warn'" />
              </div>
              <small class="uno-text-[#6f8183]">{{ rule.source }} · {{ rule.cadence }} · {{ rule.time_of_day || t('common.na') }} · {{ t('automations.nextRun', { time: rule.next_run_at || t('common.na') }) }}</small>
              <div class="uno-mt-[0.6rem] uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                <Button icon="pi pi-bolt" :label="t('automations.runNow')" severity="secondary" :disabled="!canWrite" @click="runNow(rule.id)" />
                <Button :icon="rule.enabled ? 'pi pi-pause' : 'pi pi-play'" :label="rule.enabled ? t('common.pause') : t('common.enable')" severity="secondary" :disabled="!canWrite" @click="toggleRule(rule)" />
                <Button icon="pi pi-trash" :label="t('common.delete')" severity="danger" outlined :disabled="!canWrite" @click="deleteRule(rule.id)" />
              </div>
            </div>
          </div>
          <p v-if="!rules.length" class="uno-text-[#6f8183]">{{ t('automations.noRules') }}</p>
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
import Textarea from 'primevue/textarea';
import { computed, onMounted, reactive, ref } from 'vue';

import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPatch, apiPost } from '../services/api';
import { useSession } from '../stores/session';
import type { JsonRecord } from '../utils/format';
import { buildAutomationPayload } from './automationPayload';

const session = useSession();
const canWrite = computed(() => session.canWrite.value);
const providers = ref<JsonRecord[]>([]);
const rules = ref<JsonRecord[]>([]);
const error = ref('');
const { t } = useI18n();
const form = reactive({
  name: '',
  source: 'watchlist',
  cadence: 'daily',
  weekday: 'fri',
  time: '09:00',
  tickers: '',
  enabled: true,
  llm_provider: 'openai',
  quick_think_model: '',
  deep_think_model: '',
  research_depth: 1,
  output_language: 'English',
  market_profile: 'default',
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
const providerOptions = computed(() => providers.value.map((provider) => ({
  label: provider.display_name || provider.provider,
  value: provider.provider,
})));
const selectedProvider = computed(() => providers.value.find((provider) => provider.provider === form.llm_provider));
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
const sourceOptions = computed(() => [
  { label: t('automations.sourceWatchlist'), value: 'watchlist' },
  { label: t('automations.sourceManual'), value: 'manual' },
]);
const cadenceOptions = computed(() => [
  { label: t('automations.daily'), value: 'daily' },
  { label: t('automations.weekly'), value: 'weekly' },
]);
const weekdayOptions = computed(() => [
  { label: t('automations.monday'), value: 'mon' },
  { label: t('automations.tuesday'), value: 'tue' },
  { label: t('automations.wednesday'), value: 'wed' },
  { label: t('automations.thursday'), value: 'thu' },
  { label: t('automations.friday'), value: 'fri' },
  { label: t('automations.saturday'), value: 'sat' },
  { label: t('automations.sunday'), value: 'sun' },
]);

function syncProviderModels() {
  const provider = selectedProvider.value;
  if (!form.quick_think_model) {
    form.quick_think_model = provider?.quick_models?.[0]?.value || '';
  }
  if (!form.deep_think_model) {
    form.deep_think_model = provider?.deep_models?.[0]?.value || '';
  }
}

async function loadSettingsDefaults() {
  const settings = await apiGet<JsonRecord>('/api/settings', session.apiContext.value);
  const llm = settings.llm || {};
  const analysis = settings.analysis || {};
  form.llm_provider = String(llm.provider || form.llm_provider);
  form.quick_think_model = String(llm.quick_think_model || form.quick_think_model);
  form.deep_think_model = String(llm.deep_think_model || form.deep_think_model);
  form.research_depth = Number(analysis.research_depth || form.research_depth);
  form.output_language = String(analysis.output_language || form.output_language);
  form.market_profile = String(analysis.market_profile || form.market_profile);
  form.max_risk_discuss_rounds = String(analysis.max_risk_discuss_rounds ?? form.max_risk_discuss_rounds);
  form.max_recur_limit = String(analysis.max_recur_limit ?? form.max_recur_limit);
  form.checkpoint_enabled = Boolean(analysis.checkpoint_enabled);
  form.benchmark_ticker = String(analysis.benchmark_ticker || '');
  form.backend_url = String(llm.backend_url || '');
  form.temperature = llm.temperature === null || llm.temperature === undefined ? '' : String(llm.temperature);
  form.google_thinking_level = String(llm.google_thinking_level || '');
  form.openai_reasoning_effort = String(llm.openai_reasoning_effort || '');
  form.anthropic_effort = String(llm.anthropic_effort || '');
}

async function loadProviders() {
  providers.value = await apiGet<JsonRecord[]>('/api/providers', session.apiContext.value);
  if (!selectedProvider.value && providers.value.length) {
    form.llm_provider = String(providers.value[0].provider);
  }
  syncProviderModels();
}

async function loadRules() {
  error.value = '';
  try {
    rules.value = await apiGet<JsonRecord[]>('/api/automations', session.apiContext.value);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('automations.loadError');
  }
}

async function saveRule() {
  if (!form.name.trim()) return;
  await apiPost('/api/automations', buildAutomationPayload(form), session.apiContext.value);
  Object.assign(form, {
    name: '',
    source: 'watchlist',
    cadence: 'daily',
    weekday: 'fri',
    time: '09:00',
    tickers: '',
    enabled: true,
  });
  await loadSettingsDefaults();
  syncProviderModels();
  await loadRules();
}

async function toggleRule(rule: JsonRecord) {
  await apiPatch(`/api/automations/${encodeURIComponent(String(rule.id))}`, {
    enabled: !rule.enabled,
  }, session.apiContext.value);
  await loadRules();
}

async function runNow(ruleId: string) {
  await apiPost(`/api/automations/${encodeURIComponent(ruleId)}/run-now`, {}, session.apiContext.value);
  await loadRules();
}

async function deleteRule(ruleId: string) {
  await apiDelete(`/api/automations/${encodeURIComponent(ruleId)}`, session.apiContext.value);
  await loadRules();
}

onMounted(async () => {
  await Promise.all([loadProviders(), loadSettingsDefaults()]);
  await loadRules();
});
</script>
