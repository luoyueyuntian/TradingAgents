<template>
  <section>
    <PageHeader
      :eyebrow="t('dashboard.eyebrow')"
      :title="t('dashboard.title')"
      :description="t('dashboard.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="loadAll" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <MetricGrid :items="metrics" layout="dashboard" />

    <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(320px,1fr))] uno-gap-4">
      <Card>
        <template #title>{{ t('dashboard.briefing') }}</template>
        <template #content>
          <p class="uno-text-[#6f8183]">{{ briefing?.summary?.headline || briefing?.summary?.message || t('dashboard.noBriefing') }}</p>
          <div class="uno-grid uno-gap-[0.65rem]">
            <div v-for="run in asArray(briefing?.recent_runs).slice(0, 5)" :key="run.run_id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ run.ticker }} · {{ run.date }}</span>
                <Tag :value="run.signal || run.status" :severity="signalSeverity(run.signal || run.status)" />
              </div>
              <small class="uno-text-[#6f8183]">{{ compactText(run.error || run.created_at) }}</small>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('dashboard.notifications') }}</template>
        <template #content>
          <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(180px,1fr))] uno-gap-[0.8rem] uno-mb-3">
            <Select v-model="memberFilter" :options="memberOptions" option-label="label" option-value="value" :placeholder="t('dashboard.memberFilter')" />
            <Select v-model="kindFilter" :options="kindOptions" option-label="label" option-value="value" />
            <Select v-model="severityFilter" :options="severityOptions" option-label="label" option-value="value" />
            <label class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
              <input v-model="unreadOnly" type="checkbox">
              <span>{{ t('dashboard.unreadOnly') }}</span>
            </label>
          </div>
          <div class="uno-mb-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
            <Button icon="pi pi-filter" :label="t('common.refresh')" severity="secondary" @click="loadNotifications" />
            <Button icon="pi pi-check" :label="t('dashboard.markNotificationsRead')" severity="secondary" @click="markNotificationsRead" />
            <Button icon="pi pi-download" :label="t('dashboard.exportNotifications')" severity="secondary" @click="exportNotifications" />
          </div>
          <div class="uno-grid uno-gap-[0.65rem]">
            <div v-for="item in asArray(notifications?.items).slice(0, 6)" :key="item.id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ item.title }}</span>
                <Tag :value="item.severity" :severity="item.severity === 'error' ? 'danger' : item.severity" />
              </div>
              <small class="uno-text-[#6f8183]">{{ item.message }}</small>
            </div>
          </div>
          <p v-if="!asArray(notifications?.items).length" class="uno-text-[#6f8183]">{{ t('dashboard.noNotifications') }}</p>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('dashboard.analytics') }}</template>
        <template #content>
          <div class="uno-mb-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
            <Button icon="pi pi-download" :label="t('dashboard.exportAnalytics')" severity="secondary" @click="exportAnalytics" />
          </div>
          <div class="uno-grid uno-gap-[0.65rem]">
            <div class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ t('dashboard.totalRuns') }}</span>
                <Tag :value="String(analytics?.summary?.total_runs ?? 0)" severity="info" />
              </div>
              <small class="uno-text-[#6f8183]">{{ t('dashboard.successRate') }}: {{ analytics?.summary?.success_rate ?? 0 }}</small>
            </div>
            <div v-for="item in asArray(analytics?.top_tickers).slice(0, 5)" :key="item.label" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ item.label }}</span>
                <Tag :value="String(item.value)" severity="secondary" />
              </div>
              <small class="uno-text-[#6f8183]">{{ t('dashboard.topTickers') }}</small>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('dashboard.focus') }}</template>
        <template #content>
          <div class="uno-grid uno-gap-[0.65rem]">
            <div v-for="item in dashboardFocus" :key="item.key" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ item.title }}</span>
                <Tag :value="String(item.count)" severity="info" />
              </div>
              <small class="uno-text-[#6f8183]">{{ item.description }}</small>
            </div>
          </div>
        </template>
      </Card>
    </div>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import Message from 'primevue/message';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
import { computed, onMounted, ref } from 'vue';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiGet, apiPost, buildApiUrl } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, compactText, signalSeverity, type JsonRecord } from '../utils/format';

const session = useSession();
const dashboard = ref<JsonRecord | null>(null);
const briefing = ref<JsonRecord | null>(null);
const notifications = ref<JsonRecord | null>(null);
const analytics = ref<JsonRecord | null>(null);
const members = ref<JsonRecord[]>([]);
const error = ref('');
const { t } = useI18n();
const unreadOnly = ref(false);
const memberFilter = ref('');
const kindFilter = ref('all');
const severityFilter = ref('all');
const memberOptions = computed(() => [
  { label: t('common.all'), value: '' },
  ...members.value.map((member) => ({ label: String(member.name || member.id || ''), value: String(member.name || '') })),
]);
const kindOptions = computed(() => [
  { label: t('common.all'), value: 'all' },
  { label: 'run', value: 'run' },
  { label: 'alert', value: 'alert' },
  { label: 'action', value: 'action' },
  { label: 'mention', value: 'mention' },
  { label: 'review', value: 'review' },
]);
const severityOptions = computed(() => [
  { label: t('common.all'), value: 'all' },
  { label: 'info', value: 'info' },
  { label: 'success', value: 'success' },
  { label: 'warn', value: 'warn' },
  { label: 'error', value: 'error' },
]);

const metrics = computed(() => {
  const summary = dashboard.value?.summary || {};
  const notificationSummary = notifications.value || {};
  return [
    { label: t('dashboard.metricWatchlist'), value: summary.watchlist_count ?? 0 },
    { label: t('dashboard.metricPortfolio'), value: summary.portfolio_position_count ?? 0 },
    { label: t('dashboard.metricActiveAlerts'), value: summary.active_alert_count ?? 0 },
    { label: t('dashboard.metricUnread'), value: notificationSummary.unread_count ?? 0 },
  ];
});

const dashboardFocus = computed(() => [
  {
    key: 'bullish',
    title: t('dashboard.bullishFocus'),
    count: asArray(dashboard.value?.bullish_focus).length,
    description: t('dashboard.bullishFocusDesc'),
  },
  {
    key: 'attention',
    title: t('dashboard.needsAttention'),
    count: asArray(dashboard.value?.needs_attention).length,
    description: t('dashboard.needsAttentionDesc'),
  },
  {
    key: 'actions',
    title: t('dashboard.pinnedActions'),
    count: asArray(dashboard.value?.pinned_actions).length,
    description: t('dashboard.pinnedActionsDesc'),
  },
]);

function notificationPath(base = '/api/notifications') {
  const params = new URLSearchParams();
  if (unreadOnly.value) params.set('unread_only', 'true');
  if (memberFilter.value) params.set('member', memberFilter.value);
  if (kindFilter.value && kindFilter.value !== 'all') params.set('kind', kindFilter.value);
  if (severityFilter.value && severityFilter.value !== 'all') params.set('severity', severityFilter.value);
  const query = params.toString();
  return query ? `${base}?${query}` : base;
}

async function loadNotifications() {
  notifications.value = await apiGet<JsonRecord>(notificationPath(), session.apiContext.value);
}

async function markNotificationsRead() {
  await apiPost<JsonRecord>(notificationPath('/api/notifications/read-all'), {}, session.apiContext.value);
  await loadNotifications();
}

function exportNotifications() {
  window.open(buildApiUrl(notificationPath('/api/notifications/export'), session.apiContext.value), '_blank', 'noopener');
}

function exportAnalytics() {
  window.open(buildApiUrl('/api/analytics/export', session.apiContext.value), '_blank', 'noopener');
}

async function loadAll() {
  error.value = '';
  try {
    const context = session.apiContext.value;
    const [dashboardPayload, briefingPayload, notificationPayload, memberItems, analyticsPayload] = await Promise.all([
      apiGet<JsonRecord>('/api/dashboard', context),
      apiGet<JsonRecord>('/api/briefing/daily', context),
      apiGet<JsonRecord>(notificationPath(), context),
      apiGet<JsonRecord[]>('/api/members', context),
      apiGet<JsonRecord>('/api/analytics', context),
    ]);
    dashboard.value = dashboardPayload;
    briefing.value = briefingPayload;
    notifications.value = notificationPayload;
    members.value = memberItems;
    analytics.value = analyticsPayload;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('dashboard.loadError');
  }
}

onMounted(loadAll);
</script>
