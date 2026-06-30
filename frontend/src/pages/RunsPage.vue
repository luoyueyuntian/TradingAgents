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

    <div class="content-grid" style="margin-top: 1rem;">
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
            <MetricGrid :items="detailMetrics" />
            <div class="actions-row">
              <Button icon="pi pi-refresh" :label="t('common.retry')" severity="secondary" @click="retryRun" />
              <Button icon="pi pi-trash" :label="t('common.delete')" severity="danger" outlined @click="deleteRun" />
              <a
                v-for="artifact in artifacts"
                :key="artifact.key"
                class="p-button p-component p-button-secondary"
                :href="artifact.download_url"
              >{{ artifact.label }}</a>
            </div>
            <Select v-model="selectedSectionKey" :options="sectionOptions" option-label="label" option-value="value" />
            <pre class="report-box">{{ selectedSectionText }}</pre>
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
import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPost } from '../services/api';
import { useSession } from '../stores/session';
import { compactText, signalSeverity, type JsonRecord } from '../utils/format';

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
const sectionOptions = computed(() => Object.keys(selectedRun.value?.report_sections || {}).map((key) => ({
  label: key.replaceAll('_', ' '),
  value: key,
})));
const selectedSectionText = computed(() => {
  if (!selectedRun.value) {
    return '';
  }
  const sections = selectedRun.value.report_sections || {};
  return sections[selectedSectionKey.value] || selectedRun.value.final_report || selectedRun.value.current_report || t('runs.noReport');
});

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
  const sections = Object.keys(selectedRun.value.report_sections || {});
  selectedSectionKey.value = sections[0] || '';
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
