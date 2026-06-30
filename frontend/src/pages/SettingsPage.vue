<template>
  <section>
    <PageHeader
      :eyebrow="t('settings.eyebrow')"
      :title="t('settings.title')"
      :description="t('settings.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.reload')" severity="secondary" @click="loadSettings" />
        <Button icon="pi pi-save" :label="t('common.save')" @click="saveSettings" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Message v-if="notice" severity="success" :closable="false">{{ notice }}</Message>

    <div class="wide-grid">
      <Card>
        <template #title>{{ t('settings.llmConfiguration') }}</template>
        <template #content>
          <div class="form-grid">
            <label class="field">
              <span class="field-label">{{ t('common.provider') }}</span>
              <Select v-model="form.llm.provider" :options="providerOptions" option-label="label" option-value="value" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('analysis.quickModel') }}</span>
              <InputText v-model="form.llm.quick_think_model" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('analysis.deepModel') }}</span>
              <InputText v-model="form.llm.deep_think_model" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('settings.temperature') }}</span>
              <InputText v-model="form.llm.temperature" type="number" :placeholder="t('common.default')" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('settings.backendUrl') }}</span>
              <InputText v-model="form.llm.backend_url" :placeholder="t('common.providerDefault')" />
            </label>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('settings.apiKeys') }}</template>
        <template #content>
          <div class="form-grid">
            <label v-for="keyName in apiKeyNames" :key="keyName" class="field">
              <span class="field-label">{{ keyName }}</span>
              <InputText v-model="form.api_keys[keyName]" type="password" :placeholder="t('common.notSet')" />
            </label>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('settings.analysisDefaults') }}</template>
        <template #content>
          <div class="form-grid">
            <label class="field">
              <span class="field-label">{{ t('common.language') }}</span>
              <Select v-model="form.analysis.output_language" :options="languageOptions" option-label="label" option-value="value" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('analysis.marketProfile') }}</span>
              <Select v-model="form.analysis.market_profile" :options="marketProfileOptions" option-label="label" option-value="value" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('settings.researchDepth') }}</span>
              <InputText v-model="form.analysis.research_depth" type="number" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('settings.riskRounds') }}</span>
              <InputText v-model="form.analysis.max_risk_discuss_rounds" type="number" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('settings.benchmarkTicker') }}</span>
              <InputText v-model="form.analysis.benchmark_ticker" :placeholder="t('common.auto')" />
            </label>
            <label class="inline-row">
              <input v-model="form.analysis.checkpoint_enabled" type="checkbox">
              <span>{{ t('settings.enableCheckpoint') }}</span>
            </label>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('settings.dataVendors') }}</template>
        <template #content>
          <div class="form-grid">
            <label v-for="field in vendorFields" :key="field.key" class="field">
              <span class="field-label">{{ field.label }}</span>
              <InputText v-model="form.data.data_vendors[field.key]" :placeholder="t('settings.vendorPlaceholder')" />
            </label>
          </div>
          <label class="field" style="margin-top: 0.75rem;">
            <span class="field-label">{{ t('settings.globalNewsQueries') }}</span>
            <Textarea v-model="globalNewsQueriesText" rows="4" auto-resize />
          </label>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('settings.securityWebhook') }}</template>
        <template #content>
          <div class="form-grid">
            <label class="field">
              <span class="field-label">{{ t('settings.tenantApiToken') }}</span>
              <InputText v-model="form.security.web_api_token" type="password" :placeholder="t('common.optional')" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('settings.webhookUrl') }}</span>
              <InputText v-model="form.integrations.webhook.url" placeholder="https://example.com/webhook" />
            </label>
            <label class="field">
              <span class="field-label">{{ t('settings.webhookBearerToken') }}</span>
              <InputText v-model="form.integrations.webhook.bearer_token" type="password" :placeholder="t('common.optional')" />
            </label>
            <label class="inline-row">
              <input v-model="form.integrations.webhook.enabled" type="checkbox">
              <span>{{ t('settings.enableWebhook') }}</span>
            </label>
          </div>
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
import Textarea from 'primevue/textarea';
import { computed, onMounted, reactive, ref } from 'vue';

import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiGet, apiPut } from '../services/api';
import { useSession } from '../stores/session';
import type { JsonRecord } from '../utils/format';

const session = useSession();
const providers = ref<JsonRecord[]>([]);
const error = ref('');
const notice = ref('');
const { t } = useI18n();
const apiKeyNames = ['openai', 'anthropic', 'google', 'deepseek', 'qwen', 'glm', 'minimax', 'openrouter', 'alpha_vantage'];
const vendorFields = computed(() => [
  { key: 'core_stock_apis', label: t('settings.coreStockApis') },
  { key: 'technical_indicators', label: t('settings.technicalIndicators') },
  { key: 'fundamental_data', label: t('settings.fundamentalData') },
  { key: 'news_data', label: t('settings.newsData') },
  { key: 'macro_data', label: t('settings.macroData') },
  { key: 'prediction_markets', label: t('settings.predictionMarkets') },
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

const form = reactive<JsonRecord>({
  api_keys: {},
  llm: {
    provider: 'openai',
    quick_think_model: '',
    deep_think_model: '',
    temperature: '',
    backend_url: '',
  },
  analysis: {
    output_language: 'English',
    market_profile: 'default',
    research_depth: 3,
    max_risk_discuss_rounds: 1,
    benchmark_ticker: '',
    checkpoint_enabled: false,
  },
  data: {
    data_vendors: {},
    global_news_queries: [],
  },
  security: {
    web_api_token: '',
  },
  integrations: {
    webhook: {
      enabled: false,
      url: '',
      bearer_token: '',
      event_kinds: ['run', 'alert', 'action'],
    },
  },
});

const globalNewsQueriesText = computed({
  get: () => (form.data.global_news_queries || []).join('\n'),
  set: (value: string) => {
    form.data.global_news_queries = value.split('\n').map((item) => item.trim()).filter(Boolean);
  },
});

const providerOptions = computed(() => providers.value.map((provider) => ({
  label: provider.display_name || provider.provider,
  value: provider.provider,
})));

function mergeSettings(payload: JsonRecord) {
  form.api_keys = { ...Object.fromEntries(apiKeyNames.map((key) => [key, ''])), ...(payload.api_keys || {}) };
  form.llm = { ...form.llm, ...(payload.llm || {}) };
  form.analysis = { ...form.analysis, ...(payload.analysis || {}) };
  form.data = {
    ...form.data,
    ...(payload.data || {}),
    data_vendors: { ...Object.fromEntries(vendorFields.value.map((item) => [item.key, 'default'])), ...(payload.data?.data_vendors || {}) },
  };
  form.security = { ...form.security, ...(payload.security || {}) };
  form.integrations = {
    webhook: { ...form.integrations.webhook, ...(payload.integrations?.webhook || {}) },
  };
}

async function loadSettings() {
  error.value = '';
  notice.value = '';
  try {
    const context = session.apiContext.value;
    const [settings, providerItems] = await Promise.all([
      apiGet<JsonRecord>('/api/settings', context),
      apiGet<JsonRecord[]>('/api/providers', context),
    ]);
    providers.value = providerItems;
    mergeSettings(settings);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('settings.loadError');
  }
}

function cleanMasked(value: unknown) {
  return value === '***' ? undefined : value;
}

async function saveSettings() {
  error.value = '';
  notice.value = '';
  try {
    await apiPut('/api/settings', {
      api_keys: Object.fromEntries(
        Object.entries(form.api_keys).filter(([, value]) => value && value !== '***'),
      ),
      llm: {
        ...form.llm,
        temperature: form.llm.temperature === '' ? null : Number(form.llm.temperature),
      },
      analysis: {
        ...form.analysis,
        research_depth: Number(form.analysis.research_depth || 3),
        max_risk_discuss_rounds: Number(form.analysis.max_risk_discuss_rounds || 1),
      },
      data: form.data,
      security: {
        web_api_token: cleanMasked(form.security.web_api_token),
      },
      integrations: {
        webhook: {
          ...form.integrations.webhook,
          bearer_token: cleanMasked(form.integrations.webhook.bearer_token),
        },
      },
    }, session.apiContext.value);
    notice.value = t('settings.saved');
    await loadSettings();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('settings.saveError');
  }
}

onMounted(loadSettings);
</script>
