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

    <MetricGrid :items="metrics" />

    <div class="content-grid">
      <Card>
        <template #title>{{ t('dashboard.briefing') }}</template>
        <template #content>
          <p class="muted">{{ briefing?.summary?.headline || briefing?.summary?.message || t('dashboard.noBriefing') }}</p>
          <div class="list-stack">
            <div v-for="run in asArray(briefing?.recent_runs).slice(0, 5)" :key="run.run_id" class="list-item">
              <div class="list-item-title">
                <span>{{ run.ticker }} · {{ run.date }}</span>
                <Tag :value="run.signal || run.status" :severity="signalSeverity(run.signal || run.status)" />
              </div>
              <small class="muted">{{ compactText(run.error || run.created_at) }}</small>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('dashboard.notifications') }}</template>
        <template #content>
          <div class="list-stack">
            <div v-for="item in asArray(notifications?.items).slice(0, 6)" :key="item.id" class="list-item">
              <div class="list-item-title">
                <span>{{ item.title }}</span>
                <Tag :value="item.severity" :severity="item.severity === 'error' ? 'danger' : item.severity" />
              </div>
              <small class="muted">{{ item.message }}</small>
            </div>
          </div>
          <p v-if="!asArray(notifications?.items).length" class="muted">{{ t('dashboard.noNotifications') }}</p>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('dashboard.focus') }}</template>
        <template #content>
          <div class="list-stack">
            <div v-for="item in dashboardFocus" :key="item.key" class="list-item">
              <div class="list-item-title">
                <span>{{ item.title }}</span>
                <Tag :value="String(item.count)" severity="info" />
              </div>
              <small class="muted">{{ item.description }}</small>
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
import Tag from 'primevue/tag';
import { computed, onMounted, ref } from 'vue';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiGet } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, compactText, signalSeverity, type JsonRecord } from '../utils/format';

const session = useSession();
const dashboard = ref<JsonRecord | null>(null);
const briefing = ref<JsonRecord | null>(null);
const notifications = ref<JsonRecord | null>(null);
const error = ref('');
const { t } = useI18n();

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

async function loadAll() {
  error.value = '';
  try {
    const context = session.apiContext.value;
    const [dashboardPayload, briefingPayload, notificationPayload] = await Promise.all([
      apiGet<JsonRecord>('/api/dashboard', context),
      apiGet<JsonRecord>('/api/briefing/daily', context),
      apiGet<JsonRecord>('/api/notifications', context),
    ]);
    dashboard.value = dashboardPayload;
    briefing.value = briefingPayload;
    notifications.value = notificationPayload;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('dashboard.loadError');
  }
}

onMounted(loadAll);
</script>
