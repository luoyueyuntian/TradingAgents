<template>
  <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(min(100%,280px),1fr))] uno-gap-4" data-testid="dashboard-charts">
    <Card>
      <template #title>{{ t('dashboard.activityChart') }}</template>
      <template #content>
        <p class="uno-mt-0 uno-text-xs uno-text-[#737373]">{{ t('dashboard.activityChartHint') }}</p>
        <svg v-if="maxActivity > 0" data-testid="activity-chart" viewBox="0 0 360 205" role="img" :aria-label="t('dashboard.activityChart')" class="uno-block uno-w-full">
          <title>{{ t('dashboard.activityChart') }}</title>
          <g v-for="tick in activityTicks" :key="tick">
            <line x1="36" x2="346" :y1="160 - tick / maxActivity * 130" :y2="160 - tick / maxActivity * 130" :stroke="palette.neutral[200]" />
            <text x="28" :y="164 - tick / maxActivity * 130" text-anchor="end" font-size="10" :fill="palette.neutral[500]">{{ tick }}</text>
          </g>
          <g v-for="(row,index) in activity" :key="row.label">
            <rect :x="barX(index)" :y="160 - row.value / maxActivity * 130" :width="barWidth" :height="row.value / maxActivity * 130" rx="3" :fill="palette.info[500]">
              <title>{{ row.label }} · {{ row.value }} {{ t('dashboard.runsUnit') }}</title>
            </rect>
            <text :x="barX(index) + barWidth / 2" :y="152 - row.value / maxActivity * 130" text-anchor="middle" font-size="10" :fill="palette.neutral[600]">{{ row.value }}</text>
            <text v-if="activity.length <= 5 || index === 0 || index === activity.length - 1 || index === Math.floor(activity.length / 2)" :x="barX(index) + barWidth / 2" y="183" text-anchor="middle" font-size="10" :fill="palette.neutral[500]">{{ row.label.slice(5) }}</text>
          </g>
        </svg>
        <p v-else class="uno-py-12 uno-text-center uno-text-sm uno-text-[#737373]">{{ t('dashboard.noChartData') }}</p>
        <p v-if="activity.length" class="uno-mb-0 uno-text-xs uno-text-[#737373]">{{ activity[0]?.label }} — {{ activity[activity.length - 1]?.label }}</p>
        <details v-if="activity.length" class="uno-mt-3 uno-text-sm">
          <summary class="uno-cursor-pointer uno-text-[#3d556c]">{{ t('dashboard.viewChartData') }}</summary>
          <table class="uno-mt-2 uno-w-full uno-text-left uno-text-xs">
            <thead><tr><th scope="col">{{ t('dashboard.chartDate') }}</th><th scope="col">{{ t('dashboard.chartCount') }}</th></tr></thead>
            <tbody><tr v-for="row in activity" :key="row.label"><td class="uno-py-1">{{ row.label }}</td><td>{{ row.value }}</td></tr></tbody>
          </table>
        </details>
      </template>
    </Card>
    <Card>
      <template #title>{{ t('dashboard.statusChart') }}</template>
      <template #content>
        <div v-if="statusTotal" class="uno-grid uno-grid-cols-[120px_minmax(0,1fr)] uno-items-center uno-gap-4">
          <svg data-testid="status-chart" viewBox="0 0 100 100" role="img" :aria-label="t('dashboard.statusChart')" class="uno-w-full">
            <title>{{ t('dashboard.statusChart') }}</title>
            <circle cx="50" cy="50" r="34" fill="none" :stroke="palette.neutral[100]" stroke-width="13" />
            <circle v-for="row in segments" :key="row.label" cx="50" cy="50" r="34" fill="none" :stroke="statusColor(row.label)" stroke-width="13" :stroke-dasharray="`${row.length} ${circumference}`" :stroke-dashoffset="-row.offset" transform="rotate(-90 50 50)">
              <title>{{ statusLabel(row.label) }} · {{ row.value }} {{ t('dashboard.runsUnit') }}</title>
            </circle>
            <text x="50" y="50" text-anchor="middle" dominant-baseline="middle" :font-size="statusTotal >= 100000 ? 10 : statusTotal >= 10000 ? 13 : 18" font-weight="600" :fill="palette.neutral[800]">{{ statusTotal }}</text>
            <text x="50" y="66" text-anchor="middle" font-size="8" :fill="palette.neutral[500]">{{ t('dashboard.runsUnit') }}</text>
          </svg>
          <ul class="uno-m-0 uno-grid uno-list-none uno-gap-2 uno-p-0 uno-text-sm">
            <li v-for="row in statuses" :key="row.label" class="uno-flex uno-items-center uno-justify-between uno-gap-2">
              <span class="uno-inline-flex uno-min-w-0 uno-items-center uno-gap-2"><span class="uno-h-2 uno-w-2 uno-shrink-0 uno-rounded-full" :style="{ background: statusColor(row.label) }" />{{ statusLabel(row.label) }}</span>
              <strong>{{ row.value }}</strong>
            </li>
          </ul>
        </div>
        <p v-else class="uno-py-12 uno-text-center uno-text-sm uno-text-[#737373]">{{ t('dashboard.noChartData') }}</p>
        <p class="uno-mb-0 uno-mt-4 uno-border-t uno-border-[#e5e5e5] uno-pt-3 uno-text-sm uno-text-[#737373]">{{ t('dashboard.terminalSuccessRate') }}：<strong class="uno-text-[#262626]">{{ success === null ? '—' : `${success}%` }}</strong></p>
      </template>
    </Card>
    <Card>
      <template #title>{{ t('dashboard.topTickersChart') }}</template>
      <template #content>
        <p class="uno-mt-0 uno-text-xs uno-text-[#737373]">{{ t('dashboard.topTickersChartHint') }}</p>
        <ol v-if="tickers.length" data-testid="ticker-chart" class="uno-m-0 uno-grid uno-list-none uno-gap-4 uno-p-0">
          <li v-for="row in tickers" :key="row.label">
            <div class="uno-mb-1 uno-flex uno-justify-between uno-gap-3 uno-text-sm"><span class="uno-min-w-0 uno-break-all">{{ row.label }}</span><strong class="uno-shrink-0">{{ row.value }}</strong></div>
            <div class="uno-h-2 uno-overflow-hidden uno-rounded-full uno-bg-[#f5f5f5]"><div class="uno-h-full uno-rounded-full" :style="{ width: `${row.value / maxTicker * 100}%`, background: palette.info[500] }" /></div>
          </li>
        </ol>
        <p v-else class="uno-py-12 uno-text-center uno-text-sm uno-text-[#737373]">{{ t('dashboard.noChartData') }}</p>
      </template>
    </Card>
  </div>
</template>
<script setup lang="ts">
import Card from 'primevue/card';
import { computed } from 'vue';
import { useI18n } from '../../i18n';
import { activityRows, bucketRows, successPercentage } from '../../pages/dashboardCharts';
import { palette } from '../../theme/palette';
import type { JsonRecord } from '../../utils/format';
const props = defineProps<{ analytics: JsonRecord }>();
const { t } = useI18n();
const activity = computed(() => activityRows(props.analytics.daily_activity));
const statuses = computed(() => bucketRows(props.analytics.status_breakdown));
const tickers = computed(() => bucketRows(props.analytics.top_tickers,5));
const maxActivity = computed(() => Math.max(0,...activity.value.map(row=>row.value)));
const activityTicks = computed(() => [...new Set([0, Math.ceil(maxActivity.value / 2), maxActivity.value])]);
const maxTicker = computed(() => Math.max(1,...tickers.value.map(row=>row.value)));
const statusTotal = computed(() => statuses.value.reduce((total,row)=>total+row.value,0));
const success = computed(() => successPercentage(props.analytics.summary));
const circumference = 2*Math.PI*34;
const segments = computed(() => {
  let offset=0;
  return statuses.value.map(row=>{
    const length=row.value/statusTotal.value*circumference;
    const segment={...row,length,offset}; offset+=length; return segment;
  });
});
const barWidth = computed(() => Math.min(28, 300 / Math.max(1,activity.value.length) * 0.6));
function barX(index: number) { return 40 + (index+0.5)*300 / activity.value.length - barWidth.value/2; }
function statusColor(status: string) {
  if (status==='completed') return palette.success[500];
  if (status==='failed') return palette.brand[600];
  if (['running','pending','cancelling'].includes(status)) return palette.info[500];
  return status==='cancelled' ? palette.neutral[600] : palette.neutral[400];
}
function statusLabel(status: string) {
  if (status==='completed') return t('charts.completed');
  if (status==='failed') return t('charts.failed');
  if (status==='running') return t('charts.running');
  if (status==='pending') return t('charts.pending');
  if (status==='queued') return t('charts.queued');
  if (status==='cancelled') return t('charts.cancelled');
  if (status==='cancelling') return t('charts.cancelling');
  return status;
}
</script>
