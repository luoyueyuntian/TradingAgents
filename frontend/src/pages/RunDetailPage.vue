<template>
  <section>
    <nav data-testid="run-detail-breadcrumb" class="uno-mb-3 uno-flex uno-items-center uno-gap-2 uno-text-sm uno-text-[#607174]">
      <button
        type="button"
        class="uno-inline-flex uno-cursor-pointer uno-items-center uno-gap-1 uno-border-0 uno-bg-transparent uno-p-0 uno-text-[#304345] hover:uno-text-[#132a2d]"
        @click="goBack"
      >
        <i class="pi pi-angle-left uno-text-xs" />
        <span>{{ t('common.back') }}</span>
      </button>
      <span class="uno-text-[#9ab0b1]">/</span>
      <span>{{ t('runs.runDetail') }}</span>
    </nav>

    <PageHeader
      :eyebrow="t('runs.eyebrow')"
      :title="selectedRun ? runHeaderTitle : t('runs.runDetail')"
      :description="t('runs.description')"
    >
      <template #actions>
        <div v-if="selectedRun" data-testid="run-detail-history-badge" class="uno-relative">
          <OverlayBadge :value="historyRunCount" severity="contrast">
            <Button
              data-testid="run-detail-history-toggle"
              icon="pi pi-calendar"
              severity="secondary"
              :aria-label="t('runs.historyCalendar')"
              @click="historyPickerOpen = !historyPickerOpen"
            />
          </OverlayBadge>
          <div
            v-if="historyPickerOpen"
            data-testid="run-detail-history-panel"
            class="uno-absolute uno-right-0 uno-top-[calc(100%+0.45rem)] uno-z-20 uno-grid uno-gap-3 uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3 uno-shadow-lg"
          >
            <span class="uno-text-sm uno-text-[#607174]">{{ t('runs.historySelectDate') }}</span>
            <DatePicker
              :model-value="historyPickerValue"
              inline
              date-format="yy-mm-dd"
              :manual-input="false"
              :disabled-dates="historyDisabledDates"
              :min-date="historyMinDate"
              :max-date="historyMaxDate"
              @update:model-value="handleHistoryDateSelect"
            />
          </div>
        </div>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="() => loadRunDetail()" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <details v-if="selectedRun" data-testid="run-detail-pinned-action-card" class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-px-4 uno-py-[0.85rem]">
      <summary class="uno-cursor-pointer uno-font-700">{{ t('runs.pinnedAction') }}</summary>
      <div class="uno-mt-3 uno-grid uno-grid-cols-[repeat(auto-fit,minmax(180px,1fr))] uno-gap-[0.8rem]">
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinCategory') }}</span>
          <Select v-model="pinForm.category" :options="categoryOptions" option-label="label" option-value="value" :disabled="!canWrite" />
        </label>
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinPriority') }}</span>
          <Select v-model="pinForm.priority" :options="priorityOptions" option-label="label" option-value="value" :disabled="!canWrite" />
        </label>
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinStatus') }}</span>
          <Select v-model="pinForm.action_status" :options="actionStatusOptions" option-label="label" option-value="value" :disabled="!canWrite" />
        </label>
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinAssignee') }}</span>
          <Select v-model="pinForm.assignee" :options="memberOptions" option-label="label" option-value="value" :placeholder="t('common.optional')" :disabled="!canWrite" />
        </label>
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinNextAction') }}</span>
          <InputText v-model="pinForm.next_action" :placeholder="t('runs.pinNextAction')" :disabled="!canWrite" />
        </label>
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('runs.pinDueDate') }}</span>
          <InputText v-model="pinForm.due_date" type="date" :disabled="!canWrite" />
        </label>
      </div>
      <Textarea v-model="pinForm.note" rows="3" auto-resize :placeholder="t('runs.pinNote')" class="uno-mt-3 uno-w-full" :disabled="!canWrite" />
      <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-justify-end uno-gap-[0.55rem]">
        <Button icon="pi pi-bookmark" :label="t('runs.savePinnedAction')" severity="secondary" :disabled="!canWrite" @click="savePinnedRun" />
        <Button v-if="currentPinnedRun" icon="pi pi-times" :label="t('runs.removePinnedAction')" severity="danger" outlined :disabled="!canWrite" @click="deletePinnedRun" />
      </div>
    </details>

    <Card v-if="selectedRun" data-testid="run-detail-main-card">
      <template #title>{{ t('runs.runDetail') }}</template>
      <template #content>
        <div class="uno-grid uno-gap-4">
          <div class="uno-grid uno-gap-[0.9rem] uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-[#fbfdfd] uno-p-4">
            <div class="uno-flex uno-items-start uno-justify-between uno-gap-4">
              <div>
                <p class="uno-m-0 uno-text-xs uno-font-700 uno-uppercase uno-text-[#6f8183]">{{ t('runs.summary') }}</p>
                <h2 class="uno-mb-0 uno-mt-[0.15rem] uno-text-[1.2rem] uno-tracking-normal uno-text-[#132a2d]">{{ runIdentityLabel }} · {{ selectedRun.date }}</h2>
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

          <div data-testid="run-detail-insight-panels" class="uno-grid uno-gap-3">
            <div v-for="panel in insightPanels" :key="panel.key" class="uno-min-w-0 uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-[0.85rem]">
              <span class="uno-text-[#6f8183]">{{ insightTitle(panel.key) }}</span>
              <ul v-if="panel.items.length" class="uno-mb-0 uno-mt-[0.55rem] uno-grid uno-gap-[0.45rem] uno-pl-[1.1rem] uno-leading-[1.45] uno-text-[#304345]">
                <li v-for="item in panel.items" :key="item">{{ item }}</li>
              </ul>
              <p v-else class="uno-text-[#6f8183]">{{ t('runs.noInsight') }}</p>
            </div>
          </div>

          <div
            data-testid="run-detail-section-tabs"
            class="uno-sticky uno-top-[76px] uno-z-[6] uno-rounded-xl uno-border uno-border-[#dce7e7] uno-bg-white/95 uno-p-1.5 uno-shadow-sm uno-backdrop-blur-md max-[900px]:uno-top-[128px]"
          >
            <div class="uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-3">
              <div class="uno-flex uno-flex-wrap uno-gap-1" role="tablist" :aria-label="t('runs.reportSections')">
                <button
                  v-for="section in sectionOptions"
                  :key="section.value"
                  type="button"
                  role="tab"
                  :aria-selected="selectedSectionKey === section.value"
                  :class="[
                    'uno-min-h-10 uno-cursor-pointer uno-rounded-lg uno-border-b-2 uno-border-transparent uno-px-3 uno-py-[0.55rem] uno-text-sm uno-font-600',
                    selectedSectionKey === section.value
                      ? 'uno-bg-[#162326] uno-text-white uno-shadow-sm'
                      : 'uno-bg-transparent uno-text-[#304345] hover:uno-bg-[#f4f8f8] hover:uno-text-[#132a2d]',
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
          </div>

          <ReportMarkdown
            data-testid="run-detail-report-markdown"
            :content="selectedSectionText"
            :empty-text="t('runs.noReport')"
            :constrain-height="false"
          />

          <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(280px,1fr))] uno-gap-4">
            <Card data-testid="run-detail-comments-card">
              <template #title>{{ t('runs.comments') }}</template>
              <template #content>
                <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                  <Select v-model="commentAuthor" :options="memberOptions" option-label="label" option-value="value" :placeholder="t('runs.commentAuthor')" :disabled="!canWrite" />
                </div>
                <Textarea v-model="commentBody" rows="3" auto-resize :placeholder="t('runs.commentPlaceholder')" class="uno-mt-3 uno-w-full" :disabled="!canWrite" />
                <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                  <Button icon="pi pi-comment" :label="t('runs.addComment')" severity="secondary" :disabled="!canWrite" @click="addRunComment" />
                </div>
                <div class="uno-mt-3 uno-grid uno-gap-[0.65rem]">
                  <div v-for="comment in comments" :key="comment.id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
                    <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                      <span>{{ comment.author }}</span>
                      <Tag :value="comment.resolved ? t('common.completed') : t('common.pending')" :severity="comment.resolved ? 'success' : 'warn'" />
                    </div>
                    <small class="uno-text-[#6f8183]">{{ formatDateTime(comment.created_at) }}</small>
                    <p class="uno-mb-0 uno-mt-2">{{ comment.content }}</p>
                    <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                      <Button
                        icon="pi pi-check"
                        :label="comment.resolved ? t('runs.reopenComment') : t('runs.resolveComment')"
                        severity="secondary"
                        :disabled="!canWrite"
                        @click="toggleComment(comment)"
                      />
                      <Button icon="pi pi-trash" :label="t('common.delete')" severity="danger" outlined :disabled="!canWrite" @click="deleteRunComment(comment.id)" />
                    </div>
                  </div>
                  <p v-if="!comments.length" class="uno-text-[#6f8183]">{{ t('runs.noComments') }}</p>
                </div>
              </template>
            </Card>

            <Card data-testid="run-detail-public-share-card">
              <template #title>{{ t('runs.publicShare') }}</template>
              <template #content>
                <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(180px,1fr))] uno-gap-[0.8rem]">
                  <label class="uno-grid uno-gap-[0.35rem]">
                    <span class="uno-text-[#6f8183]">{{ t('runs.shareTitle') }}</span>
                    <InputText v-model="shareForm.share_title" :placeholder="t('common.optional')" :disabled="!canWrite" />
                  </label>
                  <label class="uno-grid uno-gap-[0.35rem]">
                    <span class="uno-text-[#6f8183]">{{ t('runs.shareExpiryDays') }}</span>
                    <InputText v-model="shareForm.expires_in_days" type="number" :placeholder="t('common.optional')" :disabled="!canWrite" />
                  </label>
                </div>
                <Textarea v-model="shareForm.share_summary" rows="3" auto-resize :placeholder="t('runs.shareSummary')" class="uno-mt-3 uno-w-full" :disabled="!canWrite" />
                <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                  <Button
                    icon="pi pi-share-alt"
                    :label="currentPublicShare ? t('runs.updatePublicShare') : t('runs.createPublicShare')"
                    severity="secondary"
                    :disabled="!canWrite"
                    @click="savePublicShare"
                  />
                  <Button v-if="currentPublicShare" icon="pi pi-external-link" :label="t('common.open')" severity="secondary" @click="openPublicShare" />
                  <Button v-if="currentPublicShare" icon="pi pi-trash" :label="t('runs.deletePublicShare')" severity="danger" outlined :disabled="!canWrite" @click="deletePublicShare" />
                </div>
                <div v-if="currentPublicShare" class="uno-mt-3 uno-grid uno-gap-[0.65rem]">
                  <div class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
                    <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                      <span class="uno-break-all">{{ currentPublicShare.url }}</span>
                      <Tag :value="String(currentPublicShare.view_count || 0)" severity="info" />
                    </div>
                    <small class="uno-text-[#6f8183]">{{ formatDateTime(currentPublicShare.expires_at) }}</small>
                  </div>
                </div>
              </template>
            </Card>
          </div>

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
import DatePicker from 'primevue/datepicker';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import OverlayBadge from 'primevue/overlaybadge';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
import Textarea from 'primevue/textarea';
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import ReportMarkdown from '../components/ReportMarkdown.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPatch, apiPost, buildApiUrl } from '../services/api';
import { useSession } from '../stores/session';
import { formatDateTime, signalSeverity, type JsonRecord } from '../utils/format';
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
const members = ref<JsonRecord[]>([]);
const pinnedRuns = ref<JsonRecord[]>([]);
const comments = ref<JsonRecord[]>([]);
const historyRuns = ref<JsonRecord[]>([]);
const historyPickerOpen = ref(false);
const terminalOutput = ref('');
const selectedSectionKey = ref('');
const commentBody = ref('');
const commentAuthor = ref('');
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
  { label: t('common.created'), value: formatDateTime(selectedRun.value?.created_at) },
]);
const runIdentityLabel = computed(() => {
  if (!selectedRun.value) {
    return '';
  }
  const companyName = String(selectedRun.value.company_name || '').trim();
  const ticker = String(selectedRun.value.ticker || '').trim();
  return companyName ? `${companyName} (${ticker})` : ticker;
});
const runHeaderTitle = computed(() => (
  selectedRun.value ? `${runIdentityLabel.value} · ${selectedRun.value.date}` : ''
));
const historyRunCount = computed(() => historyRuns.value.length);
const historyRunsByDate = computed(() => {
  const byDate = new Map<string, JsonRecord>();
  for (const run of historyRuns.value) {
    const date = String(run.date || '').trim();
    if (!date) {
      continue;
    }
    const current = byDate.get(date);
    if (!current || Number(run.created_at || 0) > Number(current.created_at || 0)) {
      byDate.set(date, run);
    }
  }
  return byDate;
});
const historyPickerValue = computed(() => dateFromRunDate(selectedRun.value?.date));
const historyMinDate = computed(() => {
  const runs = historyRuns.value
    .map((run) => dateFromRunDate(run.date))
    .filter((value): value is Date => value instanceof Date)
    .sort((left, right) => left.getTime() - right.getTime());
  return runs[0];
});
const historyMaxDate = computed(() => {
  const runs = historyRuns.value
    .map((run) => dateFromRunDate(run.date))
    .filter((value): value is Date => value instanceof Date)
    .sort((left, right) => right.getTime() - left.getTime());
  return runs[0];
});
const historyDisabledDates = computed(() => {
  if (!historyMinDate.value || !historyMaxDate.value) {
    return [];
  }
  const available = new Set(historyRunsByDate.value.keys());
  const disabled: Date[] = [];
  const cursor = new Date(historyMinDate.value);
  while (cursor.getTime() <= historyMaxDate.value.getTime()) {
    const runDate = runDateFromDate(cursor);
    if (!available.has(runDate)) {
      disabled.push(new Date(cursor));
    }
    cursor.setDate(cursor.getDate() + 1);
  }
  return disabled;
});
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
const memberOptions = computed(() => members.value.map((member) => ({
  label: String(member.name || member.id || ''),
  value: String(member.name || ''),
})));
const categoryOptions = computed(() => [
  { label: t('runs.pinCategoryHighConviction'), value: 'high-conviction' },
  { label: t('runs.pinCategoryFollowUp'), value: 'follow-up' },
  { label: t('runs.pinCategoryRisk'), value: 'risk' },
  { label: t('runs.pinCategoryArchive'), value: 'archive' },
]);
const priorityOptions = computed(() => [
  { label: 'P1', value: 'p1' },
  { label: 'P2', value: 'p2' },
  { label: 'P3', value: 'p3' },
]);
const actionStatusOptions = computed(() => [
  { label: t('runs.actionTodo'), value: 'todo' },
  { label: t('runs.actionDoing'), value: 'doing' },
  { label: t('runs.actionDone'), value: 'done' },
]);
const currentPinnedRun = computed(() => pinnedRuns.value.find((item) => item.run_id === selectedRun.value?.run_id) || null);
const currentPublicShare = computed(() => selectedRun.value?.public_share || null);
const pinForm = reactive({
  note: '',
  category: 'follow-up',
  priority: 'p2',
  next_action: '',
  action_status: 'todo',
  assignee: '',
  due_date: '',
});
const shareForm = reactive({
  expires_in_days: '',
  share_title: '',
  share_summary: '',
});
const ACTIVE_RUN_STATUSES = new Set(['queued', 'pending', 'running']);
const AUTO_REFRESH_INTERVAL_MS = 5000;
let autoRefreshTimer: ReturnType<typeof setTimeout> | null = null;
let autoRefreshInFlight = false;

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

async function loadRunDetail(options: { silent?: boolean } = {}) {
  if (!routeRunId.value) return;
  const { silent = false } = options;
  error.value = '';
  if (!silent) {
    selectedRun.value = null;
    artifacts.value = [];
    historyRuns.value = [];
    historyPickerOpen.value = false;
    terminalOutput.value = '';
    selectedSectionKey.value = '';
  }
  try {
    const encodedRunId = encodeURIComponent(routeRunId.value);
    selectedRun.value = await apiGet<JsonRecord>(`/api/runs/${encodedRunId}`, session.apiContext.value);
    if (!shouldAutoRefreshRun(selectedRun.value?.status)) {
      stopAutoRefresh();
    }
    const hasOverview = Boolean(selectedRun.value.final_report || selectedRun.value.current_report);
    if (!silent || !selectedSectionKey.value) {
      selectedSectionKey.value = hasOverview ? 'overview' : orderedReportKeys.value[0] || '';
    }
    const [artifactRows, output, pinnedItems, commentItems, memberItems, runRows] = await Promise.all([
      apiGet<JsonRecord[]>(`/api/runs/${encodedRunId}/artifacts`, session.apiContext.value),
      loadTerminalOutput(encodedRunId),
      apiGet<JsonRecord[]>('/api/pinned-runs', session.apiContext.value),
      apiGet<JsonRecord[]>(`/api/runs/${encodedRunId}/comments`, session.apiContext.value),
      apiGet<JsonRecord[]>('/api/members', session.apiContext.value),
      apiGet<JsonRecord[]>('/api/runs', session.apiContext.value),
    ]);
    artifacts.value = artifactRows;
    terminalOutput.value = output;
    pinnedRuns.value = pinnedItems;
    comments.value = commentItems;
    members.value = memberItems;
    historyRuns.value = runRows
      .filter((item) => String(item.ticker || '').trim().toUpperCase() === String(selectedRun.value?.ticker || '').trim().toUpperCase())
      .sort((left, right) => Number(right.created_at || 0) - Number(left.created_at || 0));
    commentAuthor.value = session.state.currentMemberId
      ? (memberItems.find((item) => item.id === session.state.currentMemberId)?.name || '')
      : '';
    hydratePinForm();
    hydrateShareForm();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('runs.loadError');
  }
}

function normalizedRunStatus(status: unknown): string {
  return String(status || '').trim().toLowerCase();
}

function shouldAutoRefreshRun(status: unknown): boolean {
  return ACTIVE_RUN_STATUSES.has(normalizedRunStatus(status));
}

function stopAutoRefresh() {
  if (autoRefreshTimer !== null) {
    clearTimeout(autoRefreshTimer);
    autoRefreshTimer = null;
  }
}

async function refreshRunningRun() {
  if (autoRefreshInFlight) {
    return;
  }
  if (!shouldAutoRefreshRun(selectedRun.value?.status)) {
    stopAutoRefresh();
    return;
  }

  autoRefreshInFlight = true;
  try {
    await loadRunDetail({ silent: true });
  } finally {
    autoRefreshInFlight = false;
    if (shouldAutoRefreshRun(selectedRun.value?.status)) {
      ensureAutoRefresh();
      return;
    }
    stopAutoRefresh();
  }
}

function ensureAutoRefresh() {
  if (!shouldAutoRefreshRun(selectedRun.value?.status)) {
    stopAutoRefresh();
    return;
  }
  if (autoRefreshTimer !== null) {
    return;
  }
  autoRefreshTimer = setTimeout(() => {
    autoRefreshTimer = null;
    void refreshRunningRun();
  }, AUTO_REFRESH_INTERVAL_MS);
}

function hydratePinForm() {
  const current = currentPinnedRun.value;
  if (!current) {
    Object.assign(pinForm, {
      note: '',
      category: 'follow-up',
      priority: 'p2',
      next_action: '',
      action_status: 'todo',
      assignee: '',
      due_date: '',
    });
    return;
  }
  Object.assign(pinForm, {
    note: current.note || '',
    category: current.category || 'follow-up',
    priority: current.priority || 'p2',
    next_action: current.next_action || '',
    action_status: current.action_status || 'todo',
    assignee: current.assignee || '',
    due_date: current.due_date || '',
  });
}

function hydrateShareForm() {
  const current = currentPublicShare.value;
  Object.assign(shareForm, {
    expires_in_days: '',
    share_title: current?.share_title || '',
    share_summary: current?.share_summary || '',
  });
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
  const runStatus = String(selectedRun.value.status || '').trim().toLowerCase();
  if (runStatus === 'completed') {
    const runLabel = runIdentityLabel.value || String(selectedRun.value.ticker || '').trim();
    const confirmed = window.confirm(
      t('runs.retryCompletedConfirm', {
        run: runLabel,
        date: String(selectedRun.value.date || ''),
      }),
    );
    if (!confirmed) {
      return;
    }
  }
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

async function savePinnedRun() {
  if (!selectedRun.value?.run_id) return;
  await apiPost<JsonRecord>('/api/pinned-runs', {
    run_id: selectedRun.value.run_id,
    note: pinForm.note || null,
    category: pinForm.category || null,
    priority: pinForm.priority || null,
    next_action: pinForm.next_action || null,
    action_status: pinForm.action_status || null,
    assignee: pinForm.assignee || null,
    due_date: pinForm.due_date || null,
  }, session.apiContext.value);
  pinnedRuns.value = await apiGet<JsonRecord[]>('/api/pinned-runs', session.apiContext.value);
  hydratePinForm();
}

async function deletePinnedRun() {
  if (!selectedRun.value?.run_id) return;
  await apiDelete(`/api/pinned-runs/${encodeURIComponent(String(selectedRun.value.run_id))}`, session.apiContext.value);
  pinnedRuns.value = await apiGet<JsonRecord[]>('/api/pinned-runs', session.apiContext.value);
  hydratePinForm();
}

async function savePublicShare() {
  if (!selectedRun.value?.run_id) return;
  const runId = encodeURIComponent(String(selectedRun.value.run_id));
  if (!currentPublicShare.value) {
    await apiPost<JsonRecord>(`/api/runs/${runId}/public-share`, {}, session.apiContext.value);
  }
  const updatedShare = await apiPatch<JsonRecord>(
    `/api/runs/${runId}/public-share`,
    {
      expires_in_days: shareForm.expires_in_days === '' ? null : Number(shareForm.expires_in_days),
      share_title: shareForm.share_title || null,
      share_summary: shareForm.share_summary || null,
    },
    session.apiContext.value,
  );
  selectedRun.value = {
    ...selectedRun.value,
    public_share: updatedShare,
  };
  hydrateShareForm();
}

function openPublicShare() {
  if (!currentPublicShare.value?.url) return;
  window.open(currentPublicShare.value.url, '_blank', 'noopener');
}

async function deletePublicShare() {
  if (!selectedRun.value?.run_id) return;
  await apiDelete(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/public-share`,
    session.apiContext.value,
  );
  selectedRun.value = await apiGet<JsonRecord>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}`,
    session.apiContext.value,
  );
  hydrateShareForm();
}

async function addRunComment() {
  if (!selectedRun.value?.run_id || !commentAuthor.value || !commentBody.value.trim()) return;
  await apiPost<JsonRecord>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments`,
    {
      author: commentAuthor.value,
      content: commentBody.value.trim(),
    },
    session.apiContext.value,
  );
  commentBody.value = '';
  comments.value = await apiGet<JsonRecord[]>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments`,
    session.apiContext.value,
  );
}

async function toggleComment(comment: JsonRecord) {
  if (!selectedRun.value?.run_id) return;
  const resolver = comment.resolved ? null : (commentAuthor.value || comment.author);
  await apiPatch<JsonRecord>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments/${encodeURIComponent(String(comment.id))}`,
    {
      resolved: !comment.resolved,
      resolved_by: resolver,
    },
    session.apiContext.value,
  );
  comments.value = await apiGet<JsonRecord[]>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments`,
    session.apiContext.value,
  );
}

async function deleteRunComment(commentId: string) {
  if (!selectedRun.value?.run_id) return;
  await apiDelete(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments/${encodeURIComponent(commentId)}`,
    session.apiContext.value,
  );
  comments.value = await apiGet<JsonRecord[]>(
    `/api/runs/${encodeURIComponent(String(selectedRun.value.run_id))}/comments`,
    session.apiContext.value,
  );
}

async function handleHistoryDateSelect(value: Date | Date[] | (Date | null)[] | null | undefined) {
  if (!(value instanceof Date) || !selectedRun.value?.run_id) {
    return;
  }
  const selectedDate = runDateFromDate(value);
  const matched = historyRunsByDate.value.get(selectedDate);
  if (!matched?.run_id) {
    error.value = t('runs.historyUnavailable');
    return;
  }
  historyPickerOpen.value = false;
  if (String(matched.run_id) === String(selectedRun.value.run_id)) {
    return;
  }
  await router.push({ name: 'run-detail', params: { runId: String(matched.run_id) } });
}

function dateFromRunDate(value: unknown): Date | null {
  if (typeof value !== 'string') {
    return null;
  }
  const match = value.trim().match(/^(\d{4})-(\d{2})-(\d{2})$/);
  if (!match) {
    return null;
  }
  return new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3]));
}

function runDateFromDate(value: Date): string {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function goBack() {
  void router.push('/runs');
}

watch(() => selectedRun.value?.status, (status) => {
  if (shouldAutoRefreshRun(status)) {
    ensureAutoRefresh();
    return;
  }
  stopAutoRefresh();
});

watch(routeRunId, () => {
  stopAutoRefresh();
  void loadRunDetail();
}, { immediate: true });

onBeforeUnmount(() => {
  stopAutoRefresh();
});
</script>
