<template>
  <section>
    <PageHeader
      :eyebrow="t('portfolio.eyebrow')"
      :title="t('portfolio.positionsTitle')"
      :description="t('portfolio.positionsDescription')"
    >
      <template #actions>
        <Button icon="pi pi-plus" :label="t('common.addPosition')" :disabled="!canWrite" @click="openCreate" />
      </template>
    </PageHeader>

    <PortfolioSubnav />
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <MetricGrid :items="metrics" />

    <DataTable :value="positions" size="small" class="uno-rounded-xl uno-border uno-border-[#dce7e7] uno-bg-white">
      <Column field="ticker" :header="t('common.ticker')" />
      <Column field="company_name" :header="t('common.companyName')">
        <template #body="{ data }">
          {{ data.company_name || t('common.na') }}
        </template>
      </Column>
      <Column field="quantity" :header="t('portfolio.quantity')" />
      <Column field="average_cost" :header="t('portfolio.averageCost')" />
      <Column field="cost_basis" :header="t('portfolio.costBasis')" />
      <Column :header="t('common.signal')">
        <template #body="{ data }">
          <Tag :value="data.latest_signal || t('common.na')" :severity="signalSeverity(data.latest_signal)" />
        </template>
      </Column>
      <Column :header="t('common.status')">
        <template #body="{ data }">
          <Tag :value="data.latest_status || t('common.na')" :severity="signalSeverity(data.latest_status)" />
        </template>
      </Column>
      <Column field="latest_date" :header="t('common.date')">
        <template #body="{ data }">
          {{ data.latest_date || t('portfolio.noSavedRun') }}
        </template>
      </Column>
      <Column :header="t('common.created')">
        <template #body="{ data }">
          {{ formatDateTime(data.created_at) }}
        </template>
      </Column>
      <Column v-if="canWrite" :header="t('common.actions')">
        <template #body="{ data }">
          <div class="uno-flex uno-items-center uno-gap-2">
            <Button icon="pi pi-pencil" text severity="secondary" @click="openEdit(data)" />
            <Button
              :data-testid="`position-delete-${data.id}`"
              icon="pi pi-trash"
              text
              severity="danger"
              @click="removePosition(String(data.id))"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <PositionDialog v-model:visible="dialogOpen" :mode="dialogMode" :position="activePosition" @saved="loadRows" />
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import Message from 'primevue/message';
import Tag from 'primevue/tag';
import { computed, onMounted, ref } from 'vue';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import PortfolioSubnav from '../components/portfolio/PortfolioSubnav.vue';
import PositionDialog from '../components/portfolio/PositionDialog.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, formatDateTime, signalSeverity, type JsonRecord } from '../utils/format';

const session = useSession();
const canWrite = computed(() => session.canWrite.value);
const { t } = useI18n();
const payload = ref<JsonRecord | null>(null);
const error = ref('');
const dialogOpen = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const activePosition = ref<JsonRecord | null>(null);

const positions = computed(() => asArray<JsonRecord>(payload.value?.positions));
const metrics = computed(() => [
  { label: t('portfolio.positions'), value: positions.value.length },
  { label: t('portfolio.totalCostBasis'), value: Number(payload.value?.summary?.total_cost_basis || 0) },
]);

async function loadRows() {
  error.value = '';
  try {
    payload.value = await apiGet<JsonRecord>('/api/portfolio', session.apiContext.value);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('portfolio.loadError');
  }
}

function openCreate() {
  dialogMode.value = 'create';
  activePosition.value = null;
  dialogOpen.value = true;
}

function openEdit(item: JsonRecord) {
  dialogMode.value = 'edit';
  activePosition.value = item;
  dialogOpen.value = true;
}

async function removePosition(positionId: string) {
  await apiDelete(`/api/portfolio/positions/${encodeURIComponent(positionId)}`, session.apiContext.value);
  await loadRows();
}

onMounted(loadRows);
</script>
