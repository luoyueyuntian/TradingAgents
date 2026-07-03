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
        <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(220px,1fr))] uno-gap-[0.8rem]">
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('common.search') }}</span>
            <InputText v-model="filters.q" :placeholder="t('runs.searchPlaceholder')" @input="loadRuns" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('common.status') }}</span>
            <Select v-model="filters.status" :options="statusOptions" option-label="label" option-value="value" @change="loadRuns" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('runs.library') }}</span>
            <Select v-model="filters.archived" :options="archiveOptions" option-label="label" option-value="value" @change="loadRuns" />
          </label>
        </div>
      </template>
    </Card>

    <div class="uno-mt-4 uno-grid uno-items-start uno-gap-4">
      <Card>
        <template #title>{{ t('runs.recentRuns') }}</template>
        <template #content>
          <DataTable :value="runs" size="small" data-key="run_id" selection-mode="single" @row-click="openRunDetail($event.data)">
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
import { useRouter } from 'vue-router';

import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiGet } from '../services/api';
import { useSession } from '../stores/session';
import { signalSeverity, type JsonRecord } from '../utils/format';

const session = useSession();
const router = useRouter();
const runs = ref<JsonRecord[]>([]);
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

function openRunDetail(run: JsonRecord) {
  if (!run.run_id) return;
  void router.push({ name: 'run-detail', params: { runId: String(run.run_id) } });
}

onMounted(loadRuns);
</script>
