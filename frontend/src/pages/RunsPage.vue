<template>
  <section>
    <PageHeader
      :eyebrow="t('runs.eyebrow')"
      :title="t('runs.title')"
      :description="t('runs.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="loadGroups" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <Card>
      <template #content>
        <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(220px,1fr))] uno-gap-[0.8rem]">
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('common.search') }}</span>
            <InputText v-model="filters.q" :placeholder="t('runs.searchPlaceholder')" @input="resetToFirstPageAndReload" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('common.status') }}</span>
            <Select v-model="filters.status" :options="statusOptions" option-label="label" option-value="value" @change="resetToFirstPageAndReload" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('runs.library') }}</span>
            <Select v-model="filters.archived" :options="archiveOptions" option-label="label" option-value="value" @change="resetToFirstPageAndReload" />
          </label>
        </div>
      </template>
    </Card>

    <div class="uno-mt-4 uno-grid uno-gap-4">
      <Card
        v-for="group in groups.items"
        :key="String(group.group_key)"
        data-testid="runs-company-group-card"
      >
        <template #title>
          <div class="uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-3">
            <div class="uno-grid uno-gap-1">
              <strong class="uno-text-[#132a2d]">{{ group.company_name }}</strong>
              <small class="uno-text-[#6f8183]">{{ group.tickers.join(' · ') || t('common.na') }}</small>
            </div>
            <div class="uno-grid uno-justify-items-end uno-gap-1">
              <Tag :value="t('runs.companyRunCount', { count: group.run_count })" severity="info" />
              <small class="uno-text-[#6f8183]">{{ formatDateTime(group.latest_created_at) }}</small>
            </div>
          </div>
        </template>
        <template #content>
          <DataTable :value="group.recent_runs" size="small" data-key="run_id" selection-mode="single" @row-click="openRunDetail($event.data)">
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

      <Message v-if="!groups.items.length && !error" severity="info" :closable="false">{{ t('runs.noCompanyGroups') }}</Message>
    </div>

    <div class="uno-mt-4 uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-3">
      <span>{{ t('runs.companyGroupPagination', { page: groups.page, total: totalPages }) }}</span>
      <div class="uno-flex uno-gap-2">
        <Button :label="t('runs.previousPage')" severity="secondary" :disabled="groups.page <= 1" @click="goToPage(groups.page - 1)" />
        <Button :label="t('runs.nextPage')" severity="secondary" :disabled="groups.page >= totalPages" @click="goToPage(groups.page + 1)" />
      </div>
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
import { formatDateTime, signalSeverity, type JsonRecord } from '../utils/format';
import {
  buildRunCompanyGroupsPath,
  type RunCompanyGroupPage,
} from './runCompanyGroups';

const session = useSession();
const router = useRouter();
const error = ref('');
const { t } = useI18n();
const page = ref(1);
const pageSize = ref(20);
const groups = ref<RunCompanyGroupPage>({
  items: [],
  page: 1,
  page_size: 20,
  total_count: 0,
});
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
const totalPages = computed(() => Math.max(1, Math.ceil((groups.value.total_count || 0) / (groups.value.page_size || pageSize.value))));

async function loadGroups() {
  error.value = '';
  try {
    groups.value = await apiGet<RunCompanyGroupPage>(
      buildRunCompanyGroupsPath({
        q: filters.q,
        status: filters.status,
        archived: filters.archived,
        page: page.value,
        pageSize: pageSize.value,
      }),
      session.apiContext.value,
    );
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('runs.loadError');
  }
}

function resetToFirstPageAndReload() {
  page.value = 1;
  void loadGroups();
}

function goToPage(nextPage: number) {
  page.value = nextPage;
  void loadGroups();
}

function openRunDetail(run: JsonRecord) {
  if (!run.run_id) return;
  void router.push({ name: 'run-detail', params: { runId: String(run.run_id) } });
}

onMounted(loadGroups);
</script>
