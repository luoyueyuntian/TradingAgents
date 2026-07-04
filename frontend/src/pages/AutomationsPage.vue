<template>
  <section>
    <PageHeader
      :eyebrow="t('automations.eyebrow')"
      :title="t('automations.title')"
      :description="t('automations.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="loadAll" />
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

      <Card>
        <template #title>{{ t('automations.oneTimeTitle') }}</template>
        <template #content>
          <p class="uno-mb-3 uno-text-[#6f8183]">{{ t('automations.oneTimeDescription') }}</p>
          <div data-testid="one-time-task-builder" class="uno-grid uno-gap-4">
            <section
              data-testid="one-time-section-basics"
              class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3"
            >
              <div class="uno-mb-2 uno-font-700">Basics</div>
              <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(220px,1fr))] uno-gap-[0.8rem]">
                <label class="uno-grid uno-gap-1">
                  <span>Name</span>
                  <InputText
                    v-model="oneTimeForm.name"
                    data-testid="one-time-name"
                    :placeholder="t('automations.oneTimeTitle')"
                    :disabled="!canWrite"
                  />
                </label>
                <label class="uno-grid uno-gap-1">
                  <span>{{ t('automations.scheduledFor') }}</span>
                  <InputText
                    v-model="oneTimeForm.scheduledFor"
                    data-testid="one-time-scheduled-for"
                    placeholder="2026-07-10 21:30"
                    :disabled="!canWrite"
                  />
                </label>
                <label class="uno-grid uno-gap-1">
                  <span>{{ t('automations.analysisDate') }}</span>
                  <InputText
                    v-model="oneTimeForm.analysisDate"
                    data-testid="one-time-analysis-date"
                    :placeholder="t('common.date')"
                    :disabled="!canWrite"
                  />
                </label>
              </div>
            </section>

            <section
              data-testid="one-time-section-manual-stocks"
              class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3"
            >
              <div class="uno-mb-2 uno-font-700">{{ t('automations.manualStocks') }}</div>
              <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(220px,1fr))] uno-gap-[0.8rem]">
                <label class="uno-grid uno-gap-1">
                  <span>Market</span>
                  <Select
                    v-model="manualStockMarket"
                    data-testid="manual-stock-market"
                    :options="manualStockMarketOptions"
                    option-label="label"
                    option-value="value"
                    :disabled="!canWrite"
                    @change="handleManualStockMarketChange"
                  />
                </label>
                <label class="uno-grid uno-gap-1">
                  <span>Stocks</span>
                  <MultiSelect
                    v-model="selectedManualStockSymbols"
                    data-testid="manual-stock-multi"
                    :options="manualStockOptions"
                    option-label="label"
                    option-value="symbol"
                    :disabled="!canWrite"
                    @change="handleManualStockSelectionChange"
                  />
                </label>
              </div>
              <div class="uno-mt-3 uno-grid uno-gap-[0.65rem]">
                <div
                  v-for="stock in oneTimeForm.manualStocks"
                  :key="stock.symbol"
                  class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-[#f7faf9] uno-p-3"
                >
                  <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-2">
                    <span data-testid="manual-stock-symbol" class="uno-font-700">{{ stock.symbol }}</span>
                    <small class="uno-text-[#6f8183]">{{ stock.name || stock.exchange || stock.market }}</small>
                  </div>
                  <Button
                    icon="pi pi-times"
                    label="Remove"
                    severity="secondary"
                    outlined
                    :disabled="!canWrite"
                    @click="removeManualStockItem(stock.symbol)"
                  />
                </div>
                <p v-if="!oneTimeForm.manualStocks.length" class="uno-text-[#6f8183]">No manual stocks selected.</p>
              </div>
            </section>

            <section
              data-testid="one-time-section-groups-watchlist"
              class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3"
            >
              <div class="uno-mb-2 uno-font-700">{{ t('automations.stockGroups') }}</div>
              <div class="uno-grid uno-gap-[0.65rem]">
                <label
                  v-for="group in stockGroups"
                  :key="group.id"
                  class="uno-flex uno-items-center uno-gap-[0.55rem]"
                >
                  <input
                    :data-testid="`one-time-group-${group.id}`"
                    :checked="oneTimeForm.selectedGroupIds.includes(group.id)"
                    type="checkbox"
                    :disabled="!canWrite"
                    @change="toggleSelectedGroup(group.id, ($event.target as HTMLInputElement).checked)"
                  >
                  <span>{{ group.name }}</span>
                  <small class="uno-text-[#6f8183]">{{ group.tickers.join(', ') }}</small>
                </label>
                <p v-if="!stockGroups.length" class="uno-text-[#6f8183]">No stock groups available yet.</p>
              </div>
              <div v-if="selectedGroups.length" class="uno-mt-3 uno-flex uno-flex-wrap uno-gap-2">
                <span
                  v-for="group in selectedGroups"
                  :key="group.id"
                  :data-testid="`selected-group-chip-${group.id}`"
                  class="uno-inline-flex uno-items-center uno-gap-2 uno-rounded-full uno-bg-[#edf4f2] uno-px-3 uno-py-1 uno-text-sm uno-font-700 uno-text-[#243a3d]"
                >
                  {{ group.name }}
                  <button
                    type="button"
                    :data-testid="`remove-selected-group-${group.id}`"
                    class="uno-bg-transparent uno-p-0 uno-text-[#5f7376]"
                    :disabled="!canWrite"
                    @click="removeSelectedGroup(group.id)"
                  >
                    x
                  </button>
                </span>
              </div>
              <label class="uno-mt-3 uno-flex uno-items-center uno-gap-[0.55rem]">
                <input
                  v-model="oneTimeForm.includeWatchlist"
                  data-testid="one-time-include-watchlist"
                  type="checkbox"
                  :disabled="!canWrite"
                >
                <span>{{ t('automations.includeWatchlist') }}</span>
                <small class="uno-text-[#6f8183]">{{ watchlistTickers.join(', ') || t('common.na') }}</small>
              </label>
            </section>

            <section
              data-testid="one-time-section-resolved-universe"
              class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3"
            >
              <div class="uno-mb-2 uno-flex uno-items-center uno-justify-between uno-gap-3">
                <span class="uno-font-700">{{ t('automations.resolvedUniverse') }}</span>
                <span class="uno-text-sm uno-font-700 uno-text-[#5f7376]">{{ resolvedUniverseCountLabel }}</span>
              </div>
              <div class="uno-flex uno-flex-wrap uno-gap-2">
                <span
                  v-for="ticker in visibleResolvedTickers"
                  :key="ticker"
                  :data-testid="`resolved-ticker-${ticker}`"
                  class="uno-inline-flex uno-items-center uno-gap-2 uno-rounded-full uno-bg-[#edf4f2] uno-px-3 uno-py-1 uno-text-sm uno-font-700 uno-text-[#243a3d]"
                >
                  {{ ticker }}
                  <button
                    type="button"
                    :data-testid="`remove-resolved-ticker-${ticker}`"
                    class="uno-bg-transparent uno-p-0 uno-text-[#5f7376]"
                    :disabled="!canWrite"
                    @click="removeResolvedTicker(ticker)"
                  >
                    x
                  </button>
                </span>
              </div>
              <p v-if="!visibleResolvedTickers.length" class="uno-mt-2 uno-text-[#6f8183]">No stocks resolved yet.</p>
            </section>

            <section
              data-testid="one-time-section-save"
              class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3"
            >
              <div class="uno-mb-2 uno-font-700">{{ t('common.save') }}</div>
              <details class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3">
                <summary class="uno-cursor-pointer uno-font-700 uno-text-[#243a3d]">{{ t('automations.analysisConfig') }}</summary>
                <div class="uno-mt-3 uno-grid uno-grid-cols-[repeat(auto-fit,minmax(220px,1fr))] uno-gap-[0.8rem]">
                  <Select v-model="oneTimeForm.llm_provider" :options="providerOptions" option-label="label" option-value="value" :disabled="!canWrite" @change="syncProviderModels" />
                  <InputText v-model="oneTimeForm.quick_think_model" :placeholder="t('analysis.quickModel')" :disabled="!canWrite" />
                  <InputText v-model="oneTimeForm.deep_think_model" :placeholder="t('analysis.deepModel')" :disabled="!canWrite" />
                  <Select v-model="oneTimeForm.research_depth" :options="depthOptions" option-label="label" option-value="value" :disabled="!canWrite" />
                  <Select v-model="oneTimeForm.output_language" :options="languageOptions" option-label="label" option-value="value" :disabled="!canWrite" />
                  <Select v-model="oneTimeForm.market_profile" :options="marketProfileOptions" option-label="label" option-value="value" :disabled="!canWrite" />
                  <InputText v-model="oneTimeForm.max_risk_discuss_rounds" type="number" :placeholder="t('settings.riskRounds')" :disabled="!canWrite" />
                  <InputText v-model="oneTimeForm.max_recur_limit" type="number" :placeholder="t('settings.maxRecurLimit')" :disabled="!canWrite" />
                  <InputText v-model="oneTimeForm.benchmark_ticker" :placeholder="t('settings.benchmarkTicker')" :disabled="!canWrite" />
                  <InputText v-model="oneTimeForm.backend_url" :placeholder="t('settings.backendUrl')" :disabled="!canWrite" />
                  <InputText v-model="oneTimeForm.temperature" type="number" :placeholder="t('settings.temperature')" :disabled="!canWrite" />
                  <Select v-model="oneTimeForm.google_thinking_level" :options="googleThinkingOptions" option-label="label" option-value="value" :disabled="!canWrite" />
                  <Select v-model="oneTimeForm.openai_reasoning_effort" :options="reasoningEffortOptions" option-label="label" option-value="value" :disabled="!canWrite" />
                  <Select v-model="oneTimeForm.anthropic_effort" :options="reasoningEffortOptions" option-label="label" option-value="value" :disabled="!canWrite" />
                  <label class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                    <input v-model="oneTimeForm.checkpoint_enabled" type="checkbox" :disabled="!canWrite">
                    <span>{{ t('settings.enableCheckpoint') }}</span>
                  </label>
                </div>
              </details>
              <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                <Button
                  icon="pi pi-save"
                  :label="editingOneTimeTaskId ? 'Update' : t('common.save')"
                  data-testid="one-time-save"
                  :disabled="!canWrite || !visibleResolvedTickers.length"
                  @click="saveOneTimeTask"
                />
              </div>
            </section>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('automations.oneTimeTitle') }}</template>
        <template #content>
          <div data-testid="one-time-task-list" class="uno-grid uno-gap-[0.65rem]">
            <div
              v-for="task in oneTimeTasks"
              :key="String(task.id)"
              class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3"
            >
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ task.name }}</span>
                <Tag :value="formatOneTimeTaskStatus(task.status)" severity="info" />
              </div>
              <small class="uno-text-[#6f8183]">
                {{ task.scheduled_for || t('common.na') }} · {{ task.analysis_date || t('common.na') }}
              </small>
              <div class="uno-mt-2 uno-text-sm uno-text-[#5f7376]">
                {{ oneTimeTaskSourceSummary(task) }} · {{ oneTimeTaskFinalCount(task) }} stocks
              </div>
              <div class="uno-mt-2 uno-flex uno-flex-wrap uno-gap-2">
                <span
                  v-for="ticker in oneTimeTaskTickers(task)"
                  :key="ticker"
                  class="uno-rounded-full uno-bg-[#edf4f2] uno-px-3 uno-py-1 uno-text-sm uno-font-700 uno-text-[#243a3d]"
                >
                  {{ ticker }}
                </span>
              </div>
              <div
                v-if="String(task.status || '').toLowerCase() === 'scheduled'"
                class="uno-mt-[0.6rem] uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]"
              >
                <Button
                  icon="pi pi-pencil"
                  label="Edit"
                  severity="secondary"
                  :disabled="!canWrite"
                  :data-testid="`edit-one-time-task-${task.id}`"
                  @click="editOneTimeTask(task)"
                />
                <Button
                  icon="pi pi-ban"
                  label="Cancel"
                  severity="secondary"
                  outlined
                  :disabled="!canWrite"
                  :data-testid="`cancel-one-time-task-${task.id}`"
                  @click="cancelOneTimeTask(task)"
                />
              </div>
              <div
                v-else-if="String(task.status || '').toLowerCase() === 'completed' && oneTimeTaskRunIds(task).length"
                class="uno-mt-[0.6rem] uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]"
              >
                <a
                  v-for="runId in oneTimeTaskRunIds(task)"
                  :key="runId"
                  :data-testid="`completed-task-run-${runId}`"
                  :href="`/runs/${encodeURIComponent(runId)}`"
                  class="uno-rounded-full uno-border uno-border-[#dce7e7] uno-bg-white uno-px-3 uno-py-1 uno-text-sm uno-font-700 uno-text-[#243a3d]"
                >
                  {{ runId }}
                </a>
              </div>
            </div>
          </div>
          <p v-if="!oneTimeTasks.length" class="uno-text-[#6f8183]">No one-time tasks yet.</p>
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
import MultiSelect from 'primevue/multiselect';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
import Textarea from 'primevue/textarea';
import { computed, onMounted, reactive, ref } from 'vue';

import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPatch, apiPost } from '../services/api';
import { useSession } from '../stores/session';
import type { JsonRecord } from '../utils/format';
import {
  buildStockSearchPath,
  normalizeStockOptions,
  type StockCatalogOption,
} from './analyzeStockSelection';
import { buildAutomationPayload } from './automationPayload';
import { buildOneTimeTaskPayload } from './oneTimeTaskPayload';
import {
  mergeResolvedTickers,
  removeManualStock,
  upsertManualStock,
  type ManualStockPick,
  type SelectedGroup,
} from './oneTimeTaskSelection';

const session = useSession();
const canWrite = computed(() => session.canWrite.value);
const providers = ref<JsonRecord[]>([]);
const rules = ref<JsonRecord[]>([]);
const oneTimeTasks = ref<JsonRecord[]>([]);
const stockGroups = ref<SelectedGroup[]>([]);
const watchlist = ref<JsonRecord[]>([]);
const manualStockOptions = ref<Required<StockCatalogOption>[]>([]);
const manualStockMarket = ref('us');
const selectedManualStockSymbols = ref<string[]>([]);
const editingOneTimeTaskId = ref('');
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
const oneTimeForm = reactive({
  name: '',
  scheduledFor: '',
  analysisDate: '',
  manualStocks: [] as ManualStockPick[],
  selectedGroupIds: [] as string[],
  includeWatchlist: false,
  analysts: ['market'],
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
const manualStockMarketOptions = computed(() => [
  { label: 'US', value: 'us' },
  { label: 'HK', value: 'hk' },
  { label: 'CN A', value: 'cn_a' },
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
const selectedGroups = computed(() => stockGroups.value.filter((group) => oneTimeForm.selectedGroupIds.includes(group.id)));
const watchlistTickers = computed(() => watchlist.value.map((item) => String(item.ticker || '')).filter(Boolean));
const resolvedTickers = computed(() => mergeResolvedTickers({
  manualStocks: oneTimeForm.manualStocks,
  selectedGroups: selectedGroups.value,
  includeWatchlist: oneTimeForm.includeWatchlist,
  watchlistTickers: watchlistTickers.value,
}));
const visibleResolvedTickers = computed(() => resolvedTickers.value);
const resolvedUniverseCountLabel = computed(() => `${visibleResolvedTickers.value.length} stocks`);

function syncProviderModels() {
  const provider = selectedProvider.value;
  if (!form.quick_think_model) {
    form.quick_think_model = provider?.quick_models?.[0]?.value || '';
  }
  if (!form.deep_think_model) {
    form.deep_think_model = provider?.deep_models?.[0]?.value || '';
  }
  if (!oneTimeForm.quick_think_model) {
    oneTimeForm.quick_think_model = provider?.quick_models?.[0]?.value || '';
  }
  if (!oneTimeForm.deep_think_model) {
    oneTimeForm.deep_think_model = provider?.deep_models?.[0]?.value || '';
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
  oneTimeForm.llm_provider = String(llm.provider || oneTimeForm.llm_provider);
  oneTimeForm.quick_think_model = String(llm.quick_think_model || oneTimeForm.quick_think_model);
  oneTimeForm.deep_think_model = String(llm.deep_think_model || oneTimeForm.deep_think_model);
  oneTimeForm.research_depth = Number(analysis.research_depth || oneTimeForm.research_depth);
  oneTimeForm.output_language = String(analysis.output_language || oneTimeForm.output_language);
  oneTimeForm.market_profile = String(analysis.market_profile || oneTimeForm.market_profile);
  oneTimeForm.max_risk_discuss_rounds = String(analysis.max_risk_discuss_rounds ?? oneTimeForm.max_risk_discuss_rounds);
  oneTimeForm.max_recur_limit = String(analysis.max_recur_limit ?? oneTimeForm.max_recur_limit);
  oneTimeForm.checkpoint_enabled = Boolean(analysis.checkpoint_enabled);
  oneTimeForm.benchmark_ticker = String(analysis.benchmark_ticker || '');
  oneTimeForm.backend_url = String(llm.backend_url || '');
  oneTimeForm.temperature = llm.temperature === null || llm.temperature === undefined ? '' : String(llm.temperature);
  oneTimeForm.google_thinking_level = String(llm.google_thinking_level || '');
  oneTimeForm.openai_reasoning_effort = String(llm.openai_reasoning_effort || '');
  oneTimeForm.anthropic_effort = String(llm.anthropic_effort || '');
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

async function loadOneTimeTasks() {
  const payload = await apiGet<JsonRecord>('/api/one-time-tasks', session.apiContext.value);
  oneTimeTasks.value = Array.isArray(payload.items) ? payload.items : [];
}

async function loadStockGroups() {
  stockGroups.value = await apiGet<SelectedGroup[]>('/api/stock-groups', session.apiContext.value);
}

async function loadWatchlist() {
  watchlist.value = await apiGet<JsonRecord[]>('/api/watchlist', session.apiContext.value);
}

async function loadManualStockOptions() {
  const rows = await apiGet<StockCatalogOption[]>(
    buildStockSearchPath(manualStockMarket.value, '', 100),
    session.apiContext.value,
  );
  manualStockOptions.value = normalizeStockOptions(rows);
  syncSelectedManualStockSymbols();
}

function inferMarketFromSymbol(symbol: string) {
  const normalized = symbol.trim().toUpperCase();
  if (normalized.endsWith('.HK')) {
    return 'hk';
  }
  if (normalized.endsWith('.SH') || normalized.endsWith('.SZ') || normalized.endsWith('.SS')) {
    return 'cn_a';
  }
  return 'us';
}

function manualStockFromSymbol(symbol: string): ManualStockPick {
  const normalized = symbol.trim().toUpperCase();
  const knownFromCurrentOptions = manualStockOptions.value.find((item) => item.symbol === normalized);
  const knownFromForm = oneTimeForm.manualStocks.find((item) => item.symbol === normalized);
  if (knownFromCurrentOptions) {
    return {
      market: knownFromCurrentOptions.market,
      symbol: knownFromCurrentOptions.symbol,
      name: knownFromCurrentOptions.name,
      exchange: knownFromCurrentOptions.exchange,
    };
  }
  if (knownFromForm) {
    return { ...knownFromForm };
  }
  return {
    market: inferMarketFromSymbol(normalized),
    symbol: normalized,
    name: '',
    exchange: '',
  };
}

function manualStocksFromResolvedTickers(tickers: string[]) {
  return tickers.map((ticker) => manualStockFromSymbol(ticker));
}

function upsertManyManualStocks(stocks: ManualStockPick[]) {
  let next = [...oneTimeForm.manualStocks];
  for (const stock of stocks) {
    next = upsertManualStock(next, stock);
  }
  oneTimeForm.manualStocks = next;
}

function syncSelectedManualStockSymbols() {
  selectedManualStockSymbols.value = oneTimeForm.manualStocks
    .filter((stock) => stock.market === manualStockMarket.value)
    .map((stock) => stock.symbol);
}

function applyCurrentMarketSelections(symbols: string[]) {
  const normalizedSymbols = symbols.map((symbol) => symbol.trim().toUpperCase()).filter(Boolean);
  const otherMarkets = oneTimeForm.manualStocks.filter((stock) => stock.market !== manualStockMarket.value);
  const currentMarketStocks = normalizedSymbols.map((symbol) => manualStockFromSymbol(symbol));
  oneTimeForm.manualStocks = [...otherMarkets, ...currentMarketStocks];
  syncSelectedManualStockSymbols();
}

async function handleManualStockMarketChange() {
  await loadManualStockOptions();
}

function handleManualStockSelectionChange(event: { value?: string[] }) {
  applyCurrentMarketSelections(event.value || []);
}

function removeManualStockItem(symbol: string) {
  oneTimeForm.manualStocks = removeManualStock(oneTimeForm.manualStocks, symbol);
  syncSelectedManualStockSymbols();
}

function toggleSelectedGroup(groupId: string, checked: boolean) {
  const next = new Set(oneTimeForm.selectedGroupIds);
  if (checked) {
    next.add(groupId);
  } else {
    next.delete(groupId);
  }
  oneTimeForm.selectedGroupIds = [...next];
}

function removeSelectedGroup(groupId: string) {
  toggleSelectedGroup(groupId, false);
}

function removeResolvedTicker(ticker: string) {
  const normalizedTicker = ticker.trim().toUpperCase();
  if (!normalizedTicker) {
    return;
  }

  const affectedGroups = selectedGroups.value.filter((group) =>
    group.tickers.some((value) => value.trim().toUpperCase() === normalizedTicker),
  );

  if (affectedGroups.length) {
    for (const group of affectedGroups) {
      const remainingMembers = group.tickers
        .map((value) => value.trim().toUpperCase())
        .filter((value) => value && value !== normalizedTicker)
        .map((value) => manualStockFromSymbol(value));
      removeSelectedGroup(group.id);
      upsertManyManualStocks(remainingMembers);
    }
  }

  if (oneTimeForm.includeWatchlist && watchlistTickers.value.some((value) => value.trim().toUpperCase() === normalizedTicker)) {
    const remainingWatchlist = watchlistTickers.value
      .map((value) => value.trim().toUpperCase())
      .filter((value) => value && value !== normalizedTicker)
      .map((value) => manualStockFromSymbol(value));
    oneTimeForm.includeWatchlist = false;
    upsertManyManualStocks(remainingWatchlist);
  }

  oneTimeForm.manualStocks = removeManualStock(oneTimeForm.manualStocks, normalizedTicker);
  syncSelectedManualStockSymbols();
}

function resetOneTimeBuilderState() {
  Object.assign(oneTimeForm, {
    name: '',
    scheduledFor: '',
    analysisDate: '',
    manualStocks: [],
    selectedGroupIds: [],
    includeWatchlist: false,
  });
  editingOneTimeTaskId.value = '';
  selectedManualStockSymbols.value = [];
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

async function saveOneTimeTask() {
  if (!oneTimeForm.name.trim() || !oneTimeForm.scheduledFor.trim() || !oneTimeForm.analysisDate || !visibleResolvedTickers.value.length) {
    return;
  }
  const payloadForm = {
    ...oneTimeForm,
    analysts: [...oneTimeForm.analysts],
    manualStocks: oneTimeForm.manualStocks.map((stock) => ({ ...stock })),
    selectedGroupIds: [...oneTimeForm.selectedGroupIds],
    includeWatchlist: oneTimeForm.includeWatchlist,
    ...(editingOneTimeTaskId.value ? { id: editingOneTimeTaskId.value } : {}),
  };
  const requestBody = buildOneTimeTaskPayload(payloadForm as typeof oneTimeForm);
  if (editingOneTimeTaskId.value) {
    await apiPatch(`/api/one-time-tasks/${encodeURIComponent(editingOneTimeTaskId.value)}`, requestBody, session.apiContext.value);
  } else {
    await apiPost('/api/one-time-tasks', requestBody, session.apiContext.value);
  }
  resetOneTimeBuilderState();
  await loadOneTimeTasks();
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

async function loadAll() {
  error.value = '';
  try {
    await Promise.all([
      loadProviders(),
      loadSettingsDefaults(),
      loadRules(),
      loadOneTimeTasks(),
      loadStockGroups(),
      loadWatchlist(),
      loadManualStockOptions(),
    ]);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('automations.loadError');
  }
}

function formatOneTimeTaskStatus(status: unknown) {
  switch (String(status || '').toLowerCase()) {
    case 'completed':
      return t('automations.taskStatusCompleted');
    case 'missed':
      return t('automations.taskStatusMissed');
    case 'cancelled':
      return t('automations.taskStatusCancelled');
    default:
      return t('automations.taskStatusScheduled');
  }
}

function oneTimeTaskTickers(task: JsonRecord) {
  const snapshot = task.selection_snapshot;
  if (snapshot && typeof snapshot === 'object' && Array.isArray((snapshot as JsonRecord).resolved_tickers)) {
    return ((snapshot as JsonRecord).resolved_tickers as unknown[]).map((item) => String(item));
  }
  return [];
}

function oneTimeTaskSourceSummary(task: JsonRecord) {
  const snapshot = typeof task.selection_snapshot === 'object' && task.selection_snapshot ? task.selection_snapshot as JsonRecord : null;
  const manualCount = Array.isArray(snapshot?.manual_stocks) ? snapshot.manual_stocks.length : Array.isArray(task.manual_stocks) ? task.manual_stocks.length : 0;
  const groupCount = Array.isArray(snapshot?.group_snapshots) ? snapshot.group_snapshots.length : Array.isArray(task.group_ids) ? task.group_ids.length : 0;
  const includeWatchlist = snapshot?.include_watchlist === true || task.include_watchlist === true;
  const parts = [`Manual ${manualCount}`, `Groups ${groupCount}`];
  parts.push(includeWatchlist ? 'Watchlist included' : 'Watchlist off');
  return parts.join(' · ');
}

function oneTimeTaskFinalCount(task: JsonRecord) {
  return oneTimeTaskTickers(task).length;
}

function editOneTimeTask(task: JsonRecord) {
  const snapshot = typeof task.selection_snapshot === 'object' && task.selection_snapshot ? task.selection_snapshot as JsonRecord : null;
  editingOneTimeTaskId.value = String(task.id || '');
  Object.assign(oneTimeForm, {
    name: String(task.name || ''),
    scheduledFor: String(task.scheduled_for || ''),
    analysisDate: String(task.analysis_date || ''),
    manualStocks: Array.isArray(snapshot?.manual_stocks)
      ? (snapshot.manual_stocks as ManualStockPick[]).map((stock) => ({ ...manualStockFromSymbol(String(stock.symbol || '')), ...stock }))
      : Array.isArray(task.manual_stocks)
        ? (task.manual_stocks as ManualStockPick[]).map((stock) => ({ ...stock }))
        : [],
    selectedGroupIds: Array.isArray(snapshot?.group_snapshots)
      ? (snapshot.group_snapshots as JsonRecord[]).map((group) => String(group.id || '')).filter(Boolean)
      : Array.isArray(task.group_ids)
        ? (task.group_ids as unknown[]).map((groupId) => String(groupId)).filter(Boolean)
        : [],
    includeWatchlist: snapshot?.include_watchlist === true || task.include_watchlist === true,
  });
  syncSelectedManualStockSymbols();
}

async function cancelOneTimeTask(task: JsonRecord) {
  await apiPost(`/api/one-time-tasks/${encodeURIComponent(String(task.id || ''))}/cancel`, {}, session.apiContext.value);
  await loadOneTimeTasks();
}

function oneTimeTaskRunIds(task: JsonRecord) {
  if (!Array.isArray(task.run_ids)) {
    return [];
  }
  return (task.run_ids as unknown[]).map((value) => String(value)).filter(Boolean);
}

onMounted(async () => {
  await loadAll();
});
</script>
