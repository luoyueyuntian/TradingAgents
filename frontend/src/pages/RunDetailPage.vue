<template>
  <section>
    <PageHeader
      :eyebrow="t('runs.eyebrow')"
      :title="selectedRun ? `${selectedRun.ticker} · ${selectedRun.date}` : t('runs.runDetail')"
      :description="t('runs.description')"
    >
      <template #actions>
        <Button icon="pi pi-arrow-left" :label="t('nav.runs')" severity="secondary" @click="goBack" />
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="loadRunDetail" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <Card v-if="selectedRun">
      <template #title>{{ t('runs.runDetail') }}</template>
      <template #content>
        <div class="uno-grid uno-gap-4">
          <div class="uno-grid uno-gap-[0.9rem] uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-[#fbfdfd] uno-p-4">
            <div class="uno-flex uno-items-start uno-justify-between uno-gap-4">
              <div>
                <p class="uno-m-0 uno-text-xs uno-font-700 uno-uppercase uno-text-[#6f8183]">{{ t('runs.summary') }}</p>
                <h2 class="uno-mb-0 uno-mt-[0.15rem] uno-text-[1.2rem] uno-tracking-normal uno-text-[#132a2d]">{{ selectedRun.ticker }} · {{ selectedRun.date }}</h2>
              </div>
              <Tag :value="selectedRun.signal || selectedRun.status" :severity="signalSeverity(selectedRun.signal || selectedRun.status)" />
            </div>
            <MetricGrid :items="detailMetrics" />
            <div class="uno-grid uno-grid-cols-4 max-[1100px]:uno-grid-cols-2 max-[640px]:uno-grid-cols-1 uno-gap-[0.65rem]">
              <div v-for="item in decisionItems" :key="item.label" class="uno-grid uno-min-w-0 uno-gap-1 uno-rounded-lg uno-border uno-border-[#dbe6e6] uno-bg-white uno-p-3">
                <span class="uno-text-[0.78rem] uno-text-[#607174]">{{ item.label }}</span>
                <strong class="uno-min-w-0 uno-break-words uno-text-[#132a2d]">{{ item.value }}</strong>
              </div>
            </div>
            <p class="uno-m-0 uno-leading-[1.55] uno-text-[#304345]">{{ decisionSummary }}</p>
          </div>

          <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(210px,1fr))] uno-gap-3">
            <div v-for="panel in insightPanels" :key="panel.key" class="uno-min-w-0 uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-[0.85rem]">
              <span class="uno-text-[#6f8183]">{{ insightTitle(panel.key) }}</span>
              <ul v-if="panel.items.length" class="uno-mb-0 uno-mt-[0.55rem] uno-grid uno-gap-[0.45rem] uno-pl-[1.1rem] uno-leading-[1.45] uno-text-[#304345]">
                <li v-for="item in panel.items" :key="item">{{ item }}</li>
              </ul>
              <p v-else class="uno-text-[#6f8183]">{{ t('runs.noInsight') }}</p>
            </div>
          </div>

          <div class="uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-3">
            <div class="uno-flex uno-flex-wrap uno-gap-[0.35rem]" role="tablist" :aria-label="t('runs.reportSections')">
              <button
                v-for="section in sectionOptions"
                :key="section.value"
                type="button"
                role="tab"
                :aria-selected="selectedSectionKey === section.value"
                :class="[
                  'uno-min-h-9 uno-cursor-pointer uno-rounded-lg uno-border uno-px-3 uno-py-[0.45rem]',
                  selectedSectionKey === section.value
                    ? 'uno-border-[#162326] uno-bg-[#162326] uno-text-white'
                    : 'uno-border-[#d5e2e2] uno-bg-white uno-text-[#304345] hover:uno-border-[#90a9aa]',
                ]"
                @click="selectedSectionKey = section.value"
              >
                {{ section.label }}
              </button>
            </div>
            <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
              <Button icon="pi pi-refresh" :label="t('common.retry')" severity="secondary" :disabled="!canWrite" @click="retryRun" />
              <Button icon="pi pi-trash" :label="t('common.delete')" severity="danger" outlined :disabled="!canWrite" @click="deleteRun" />
            </div>
          </div>

          <ReportMarkdown :content="selectedSectionText" :empty-text="t('runs.noReport')" />

          <details class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-px-4 uno-py-[0.85rem]">
            <summary class="uno-cursor-pointer uno-font-700">{{ t('runs.terminalOutput') }}</summary>
            <pre class="uno-m-0 uno-mt-3 uno-max-h-[460px] uno-overflow-auto uno-whitespace-pre-wrap uno-break-words uno-rounded-lg uno-bg-[#101b1d] uno-p-[0.85rem] uno-text-[#d8f3ee]">{{ terminalOutput || t('runs.noTerminalOutput') }}</pre>
          </details>

          <details v-if="artifacts.length" class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-px-4 uno-py-[0.85rem]">
            <summary class="uno-cursor-pointer uno-font-700">{{ t('runs.artifacts') }}</summary>
            <div class="uno-mt-3 uno-flex uno-flex-wrap uno-gap-2">
              <a
                v-for="artifact in artifacts"
                :key="artifact.key"
                class="uno-inline-flex uno-min-h-[34px] uno-items-center uno-rounded-lg uno-border uno-border-[#d5e2e2] uno-px-[0.65rem] uno-py-1.5 uno-text-[#162326] uno-no-underline hover:uno-border-[#90a9aa] hover:uno-bg-[#f4f8f8]"
                :href="artifact.download_url"
              >{{ artifact.label }}</a>
            </div>
          </details>
        </div>
      </template>
    </Card>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import Message from 'primevue/message';
import Tag from 'primevue/tag';
import { computed, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import ReportMarkdown from '../components/ReportMarkdown.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPost, buildApiUrl } from '../services/api';
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
const route = useRoute();
const router = useRouter();
const canWrite = computed(() => session.canWrite.value);
const selectedRun = ref<JsonRecord | null>(null);
const artifacts = ref<JsonRecord[]>([]);
const terminalOutput = ref('');
const selectedSectionKey = ref('');
const error = ref('');
const { t } = useI18n();

const routeRunId = computed(() => {
  const value = route.params.runId;
  return Array.isArray(value) ? String(value[0] || '') : String(value || '');
});
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

async function loadRunDetail() {
  if (!routeRunId.value) return;
  error.value = '';
  selectedRun.value = null;
  artifacts.value = [];
  terminalOutput.value = '';
  selectedSectionKey.value = '';
  try {
    const encodedRunId = encodeURIComponent(routeRunId.value);
    selectedRun.value = await apiGet<JsonRecord>(`/api/runs/${encodedRunId}`, session.apiContext.value);
    const hasOverview = Boolean(selectedRun.value.final_report || selectedRun.value.current_report);
    selectedSectionKey.value = hasOverview ? 'overview' : orderedReportKeys.value[0] || '';
    const [artifactRows, output] = await Promise.all([
      apiGet<JsonRecord[]>(`/api/runs/${encodedRunId}/artifacts`, session.apiContext.value),
      loadTerminalOutput(encodedRunId),
    ]);
    artifacts.value = artifactRows;
    terminalOutput.value = output;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('runs.loadError');
  }
}

async function loadTerminalOutput(encodedRunId: string) {
  const response = await fetch(buildApiUrl(`/api/runs/${encodedRunId}/terminal-output`, session.apiContext.value), {
    credentials: 'same-origin',
  });
  if (!response.ok) {
    throw new Error(response.statusText || t('runs.terminalOutputLoadError'));
  }
  return response.text();
}

async function retryRun() {
  if (!selectedRun.value?.run_id) return;
  const created = await apiPost<JsonRecord>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/retry`,
    {},
    session.apiContext.value,
  );
  if (created.run_id) {
    await router.push({ name: 'run-detail', params: { runId: String(created.run_id) } });
    return;
  }
  selectedRun.value = created;
  terminalOutput.value = '';
}

async function deleteRun() {
  if (!selectedRun.value?.run_id) return;
  await apiDelete(`/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}`, session.apiContext.value);
  await router.push('/runs');
}

function goBack() {
  void router.push('/runs');
}

watch(routeRunId, loadRunDetail, { immediate: true });
</script>
