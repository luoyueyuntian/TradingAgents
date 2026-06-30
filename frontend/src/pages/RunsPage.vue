<template>
  <section>
    <PageHeader
      :eyebrow="t('runs.eyebrow')"
      :title="t('runs.title')"
      :description="t('runs.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="loadRuns" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <Card>
      <template #content>
        <div class="form-grid">
          <label class="field">
            <span class="field-label">{{ t('common.search') }}</span>
            <InputText v-model="filters.q" :placeholder="t('runs.searchPlaceholder')" @input="loadRuns" />
          </label>
          <label class="field">
            <span class="field-label">{{ t('common.status') }}</span>
            <Select v-model="filters.status" :options="statusOptions" option-label="label" option-value="value" @change="loadRuns" />
          </label>
          <label class="field">
            <span class="field-label">{{ t('runs.library') }}</span>
            <Select v-model="filters.archived" :options="archiveOptions" option-label="label" option-value="value" @change="loadRuns" />
          </label>
        </div>
      </template>
    </Card>

    <div class="runs-grid" style="margin-top: 1rem;">
      <Card>
        <template #title>{{ t('runs.recentRuns') }}</template>
        <template #content>
          <DataTable :value="runs" size="small" data-key="run_id" selection-mode="single" @row-click="openRun($event.data)">
            <Column field="ticker" :header="t('common.ticker')" />
            <Column field="date" :header="t('common.date')" />
            <Column field="status" :header="t('common.status')">
              <template #body="{ data }">
                <Tag :value="data.status" :severity="signalSeverity(data.status)" />
              </template>
            </Column>
            <Column field="signal" :header="t('common.signal')">
              <template #body="{ data }">
                <Tag :value="data.signal || t('common.na')" :severity="signalSeverity(data.signal)" />
              </template>
            </Column>
          </DataTable>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('runs.runDetail') }}</template>
        <template #content>
          <div v-if="selectedRun" class="wide-grid">
            <div class="run-summary-panel">
              <div class="summary-heading">
                <div>
                  <p class="eyebrow">{{ t('runs.summary') }}</p>
                  <h2>{{ selectedRun.ticker }} · {{ selectedRun.date }}</h2>
                </div>
                <Tag :value="selectedRun.signal || selectedRun.status" :severity="signalSeverity(selectedRun.signal || selectedRun.status)" />
              </div>
              <MetricGrid :items="detailMetrics" />
              <div class="decision-grid">
                <div v-for="item in decisionItems" :key="item.label" class="decision-item">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>
              <p class="decision-thesis">{{ decisionSummary }}</p>
            </div>

            <div class="insight-grid">
              <div v-for="panel in insightPanels" :key="panel.key" class="insight-panel">
                <span class="field-label">{{ insightTitle(panel.key) }}</span>
                <ul v-if="panel.items.length" class="insight-list">
                  <li v-for="item in panel.items" :key="item">{{ item }}</li>
                </ul>
                <p v-else class="muted">{{ t('runs.noInsight') }}</p>
              </div>
            </div>

            <div class="report-toolbar">
              <div class="report-tabs" role="tablist" :aria-label="t('runs.reportSections')">
                <button
                  v-for="section in sectionOptions"
                  :key="section.value"
                  type="button"
                  role="tab"
                  :aria-selected="selectedSectionKey === section.value"
                  :class="['report-tab', { active: selectedSectionKey === section.value }]"
                  @click="selectedSectionKey = section.value"
                >
                  {{ section.label }}
                </button>
              </div>
              <div class="actions-row">
                <Button icon="pi pi-refresh" :label="t('common.retry')" severity="secondary" @click="retryRun" />
                <Button icon="pi pi-trash" :label="t('common.delete')" severity="danger" outlined @click="deleteRun" />
              </div>
            </div>

            <ReportMarkdown :content="selectedSectionText" :empty-text="t('runs.noReport')" />

            <details v-if="artifacts.length" class="artifact-panel">
              <summary>{{ t('runs.artifacts') }}</summary>
              <div class="artifact-links">
                <a
                  v-for="artifact in artifacts"
                  :key="artifact.key"
                  class="artifact-link"
                  :href="artifact.download_url"
                >{{ artifact.label }}</a>
              </div>
            </details>
          </div>
          <p v-else class="muted">{{ t('runs.selectRun') }}</p>
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
import ReportMarkdown from '../components/ReportMarkdown.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPost } from '../services/api';
import { useSession } from '../stores/session';
import { compactText, signalSeverity, type JsonRecord } from '../utils/format';
import { buildDecisionHighlights, buildInsightPanels } from '../utils/runDisplay';

const SECTION_ORDER = [
  'market_report',
  'sentiment_report',
  'news_report',
  'fundamentals_report',
  'investment_plan',
  'trader_investment_plan',
  'final_trade_decision',
];

const session = useSession();
const runs = ref<JsonRecord[]>([]);
const selectedRun = ref<JsonRecord | null>(null);
const artifacts = ref<JsonRecord[]>([]);
const selectedSectionKey = ref('');
const error = ref('');
const { t } = useI18n();
const filters = reactive({
  q: '',
  status: '',
  archived: 'active',
});

const statusOptions = computed(() => [
  { label: t('common.all'), value: '' },
  { label: t('common.queued'), value: 'queued' },
  { label: t('common.running'), value: 'running' },
  { label: t('common.completed'), value: 'completed' },
  { label: t('common.failed'), value: 'failed' },
  { label: t('common.cancelled'), value: 'cancelled' },
]);
const archiveOptions = computed(() => [
  { label: t('common.active'), value: 'active' },
  { label: t('common.archived'), value: 'archived' },
  { label: t('common.all'), value: 'all' },
]);

const detailMetrics = computed(() => [
  { label: t('common.runId'), value: selectedRun.value?.run_id || t('common.na') },
  { label: t('common.ticker'), value: selectedRun.value?.ticker || t('common.na') },
  { label: t('common.provider'), value: selectedRun.value?.config_summary?.llm_provider || t('common.na') },
  { label: t('common.created'), value: compactText(selectedRun.value?.created_at) },
]);
const orderedReportKeys = computed(() => {
  const sections = selectedRun.value?.report_sections || {};
  const keys = Object.keys(sections);
  return [
    ...SECTION_ORDER.filter((key) => keys.includes(key)),
    ...keys.filter((key) => !SECTION_ORDER.includes(key)),
  ];
});
const sectionOptions = computed(() => {
  if (!selectedRun.value) {
    return [];
  }
  const options = orderedReportKeys.value.map((key) => ({
    label: sectionLabel(key),
    value: key,
  }));
  if (selectedRun.value.final_report || selectedRun.value.current_report) {
    return [{ label: sectionLabel('overview'), value: 'overview' }, ...options];
  }
  return options;
});
const selectedSectionText = computed(() => {
  if (!selectedRun.value) {
    return '';
  }
  if (selectedSectionKey.value === 'overview') {
    return selectedRun.value.final_report || selectedRun.value.current_report || '';
  }
  const sections = selectedRun.value.report_sections || {};
  return sections[selectedSectionKey.value] || '';
});
const decisionHighlights = computed(() => buildDecisionHighlights(
  selectedRun.value?.report_sections || {},
  selectedRun.value?.signal,
));
const decisionSummary = computed(() => (
  decisionHighlights.value.summary || t('runs.summaryFallback')
));
const decisionItems = computed(() => [
  {
    label: t('runs.finalRating'),
    value: decisionHighlights.value.finalRating || t('common.pending'),
  },
  {
    label: t('runs.tradeAction'),
    value: decisionHighlights.value.tradeAction || t('common.na'),
  },
  {
    label: t('runs.priceTarget'),
    value: decisionHighlights.value.priceTarget || t('common.na'),
  },
  {
    label: t('runs.riskControl'),
    value: decisionHighlights.value.riskControl || t('common.na'),
  },
]);
const insightActionLabels = computed(() => ({
  action: t('runs.actionLabel.action'),
  entry: t('runs.actionLabel.entry'),
  stopLoss: t('runs.actionLabel.stopLoss'),
  sizing: t('runs.actionLabel.sizing'),
}));
const insightPanels = computed(() => buildInsightPanels(
  selectedRun.value?.report_sections || {},
  insightActionLabels.value,
));

function sectionLabel(key: string): string {
  switch (key) {
    case 'overview':
      return t('runs.section.overview');
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

function insightTitle(key: 'evidence' | 'risks' | 'actions'): string {
  switch (key) {
    case 'evidence':
      return t('runs.insight.evidence');
    case 'risks':
      return t('runs.insight.risks');
    case 'actions':
      return t('runs.insight.actions');
  }
}

function buildQuery() {
  const params = new URLSearchParams();
  if (filters.q.trim()) params.set('q', filters.q.trim());
  if (filters.status) params.set('status', filters.status);
  if (filters.archived) params.set('archived', filters.archived);
  const query = params.toString();
  return query ? `/api/runs?${query}` : '/api/runs';
}

async function loadRuns() {
  error.value = '';
  try {
    runs.value = await apiGet<JsonRecord[]>(buildQuery(), session.apiContext.value);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('runs.loadError');
  }
}

async function openRun(run: JsonRecord) {
  selectedRun.value = await apiGet<JsonRecord>(`/api/runs/${encodeURIComponent(String(run.run_id))}`, session.apiContext.value);
  const hasOverview = Boolean(selectedRun.value.final_report || selectedRun.value.current_report);
  selectedSectionKey.value = hasOverview ? 'overview' : orderedReportKeys.value[0] || '';
  artifacts.value = await apiGet<JsonRecord[]>(`/api/runs/${encodeURIComponent(String(run.run_id))}/artifacts`, session.apiContext.value);
}

async function retryRun() {
  if (!selectedRun.value?.run_id) return;
  const created = await apiPost<JsonRecord>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/retry`,
    {},
    session.apiContext.value,
  );
  await loadRuns();
  selectedRun.value = created;
}

async function deleteRun() {
  if (!selectedRun.value?.run_id) return;
  await apiDelete(`/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}`, session.apiContext.value);
  selectedRun.value = null;
  artifacts.value = [];
  await loadRuns();
}

onMounted(loadRuns);
</script>
