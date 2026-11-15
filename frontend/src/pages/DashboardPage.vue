<template>
  <section>
    <PageHeader :eyebrow="t('dashboard.eyebrow')" :title="t('dashboard.title')" :description="t('dashboard.description')">
      <template #actions><Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" :loading="loading" @click="loadAll" /></template>
    </PageHeader>
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <MetricGrid :items="metrics" layout="dashboard" />
    <div class="uno-mb-3 uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-3">
      <h2 class="uno-m-0 uno-text-lg uno-font-semibold">{{ t('dashboard.analytics') }}</h2>
      <Button icon="pi pi-download" :label="t('dashboard.exportAnalytics')" severity="secondary" :disabled="!analytics" @click="exportAnalytics" />
    </div>
    <DashboardCharts v-if="analytics" :analytics="analytics" />
    <p v-else-if="loading" role="status" class="uno-text-[#737373]">{{ t('dashboard.chartsLoading') }}</p>
    <div class="uno-mt-4 uno-grid uno-grid-cols-[repeat(auto-fit,minmax(min(100%,320px),1fr))] uno-gap-4">
      <Card>
        <template #title>{{ t('dashboard.briefing') }}</template>
        <template #content>
          <p class="uno-text-[#737373]">{{ briefing?.summary?.headline || briefing?.summary?.message || t('dashboard.noBriefing') }}</p>
          <div class="uno-grid uno-gap-[0.65rem]">
            <div v-for="run in asArray(briefing?.recent_runs).slice(0, 5)" :key="run.run_id" class="uno-rounded-lg uno-border uno-border-[#e5e5e5] uno-bg-white uno-p-3">
              <div class="uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <RouterLink :to="`/runs/${encodeURIComponent(run.run_id)}`" class="uno-text-inherit uno-no-underline hover:uno-underline">{{ run.ticker }} · {{ run.date }}</RouterLink>
                <Tag :value="run.signal || run.status" :severity="signalSeverity(run.signal || run.status)" />
              </div>
              <small class="uno-text-[#737373]">{{ run.error ? compactText(run.error) : formatDateTime(run.created_at) }}</small>
            </div>
          </div>
        </template>
      </Card>
      <Card>
        <template #title>{{ t('dashboard.focus') }}</template>
        <template #content>
          <div class="uno-grid uno-gap-[0.65rem]">
            <div v-for="item in dashboardFocus" :key="item.key" class="uno-rounded-lg uno-border uno-border-[#e5e5e5] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700"><span>{{ item.title }}</span><Tag :value="String(item.count)" severity="info" /></div>
              <small class="uno-text-[#737373]">{{ item.description }}</small>
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
import { RouterLink } from 'vue-router';
import DashboardCharts from '../components/dashboard/DashboardCharts.vue';
import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiGet, buildApiUrl } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, compactText, formatDateTime, signalSeverity, type JsonRecord } from '../utils/format';
const session = useSession();
const { t } = useI18n();
const dashboard = ref<JsonRecord | null>(null);
const briefing = ref<JsonRecord | null>(null);
const analytics = ref<JsonRecord | null>(null);
const loading = ref(false);
const error = ref('');
const metrics = computed(() => {
  const summary=dashboard.value?.summary || {};
  return [
    { label:t('dashboard.metricWatchlist'), value:dashboard.value ? summary.watchlist_count ?? 0 : '—' },
    { label:t('dashboard.metricPortfolio'), value:dashboard.value ? summary.portfolio_position_count ?? 0 : '—' },
    { label:t('dashboard.metricAlertHits'), value:dashboard.value ? summary.alert_hit_count ?? 0 : '—' },
    { label:t('dashboard.totalRuns'), value:analytics.value ? analytics.value.summary?.total_runs ?? 0 : '—' },
  ];
});
const dashboardFocus = computed(() => [
  {key:'bullish',title:t('dashboard.bullishFocus'),count:dashboard.value?.summary?.bullish_focus_count ?? asArray(dashboard.value?.bullish_focus).length,description:t('dashboard.bullishFocusDesc')},
  {key:'attention',title:t('dashboard.needsAttention'),count:dashboard.value?.summary?.needs_attention_count ?? asArray(dashboard.value?.needs_attention).length,description:t('dashboard.needsAttentionDesc')},
  {key:'actions',title:t('dashboard.pinnedActions'),count:dashboard.value?.summary?.pinned_action_count ?? asArray(dashboard.value?.pinned_actions).length,description:t('dashboard.pinnedActionsDesc')},
]);
function exportAnalytics() { window.open(buildApiUrl('/api/analytics/export',session.apiContext.value),'_blank','noopener'); }
let generation=0;
async function loadAll() {
  const requestId=++generation;
  error.value=''; loading.value=true;
  const context={...session.apiContext.value};
  try {
    const [dashboardPayload,briefingPayload,analyticsPayload]=await Promise.all([
      apiGet<JsonRecord>('/api/dashboard',context), apiGet<JsonRecord>('/api/briefing/daily',context), apiGet<JsonRecord>('/api/analytics',context),
    ]);
    if (requestId!==generation || context.tenantId!==session.apiContext.value.tenantId) return;
    dashboard.value=dashboardPayload; briefing.value=briefingPayload; analytics.value=analyticsPayload;
  } catch (exc) { if(requestId===generation) error.value=exc instanceof Error ? exc.message : t('dashboard.loadError'); }
  finally { if(requestId===generation) loading.value=false; }
}
onMounted(loadAll);
</script>
