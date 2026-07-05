<template>
  <section>
    <PageHeader
      :eyebrow="t('portfolio.eyebrow')"
      :title="t('portfolio.stockGroupsTitle')"
      :description="t('portfolio.stockGroupsDescription')"
    >
      <template #actions>
        <Button icon="pi pi-plus" :label="t('common.add')" :disabled="!canWrite" @click="openCreate" />
      </template>
    </PageHeader>

    <PortfolioSubnav />
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <MetricGrid :items="metrics" />

    <DataTable :value="groups" size="small" class="uno-rounded-xl uno-border uno-border-[#dce7e7] uno-bg-white">
      <Column field="name" :header="t('portfolio.stockGroupName')" />
      <Column :header="t('portfolio.stockGroupTickers')">
        <template #body="{ data }">
          {{
            asArray<string>(data.tickers)
              .map((ticker) => {
                const companyName = data.company_names?.[ticker];
                return companyName ? `${ticker} · ${companyName}` : ticker;
              })
              .join(', ')
          }}
        </template>
      </Column>
      <Column field="created_at" :header="t('common.created')">
        <template #body="{ data }">
          {{ formatDateTime(data.created_at) }}
        </template>
      </Column>
      <Column field="updated_at" :header="t('common.updated')">
        <template #body="{ data }">
          {{ formatDateTime(data.updated_at) }}
        </template>
      </Column>
      <Column v-if="canWrite" :header="t('common.actions')">
        <template #body="{ data }">
          <div class="uno-flex uno-gap-2">
            <Button icon="pi pi-pencil" text severity="secondary" @click="openEdit(data)" />
            <Button
              :data-testid="`stock-group-delete-${data.id}`"
              icon="pi pi-trash"
              text
              severity="danger"
              @click="removeGroup(String(data.id))"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <StockGroupDialog v-model:visible="dialogOpen" :mode="dialogMode" :group="activeGroup" @saved="loadRows" />
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import Message from 'primevue/message';
import { computed, onMounted, ref } from 'vue';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import PortfolioSubnav from '../components/portfolio/PortfolioSubnav.vue';
import StockGroupDialog from '../components/portfolio/StockGroupDialog.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, formatDateTime, type JsonRecord } from '../utils/format';

const session = useSession();
const canWrite = computed(() => session.canWrite.value);
const { t } = useI18n();
const groups = ref<JsonRecord[]>([]);
const error = ref('');
const dialogOpen = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const activeGroup = ref<JsonRecord | null>(null);

const metrics = computed(() => [
  { label: t('portfolio.stockGroups'), value: groups.value.length },
]);

async function loadRows() {
  error.value = '';
  try {
    groups.value = await apiGet<JsonRecord[]>('/api/stock-groups', session.apiContext.value);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('portfolio.loadError');
  }
}

function openCreate() {
  dialogMode.value = 'create';
  activeGroup.value = null;
  dialogOpen.value = true;
}

function openEdit(group: JsonRecord) {
  dialogMode.value = 'edit';
  activeGroup.value = group;
  dialogOpen.value = true;
}

async function removeGroup(groupId: string) {
  await apiDelete(`/api/stock-groups/${encodeURIComponent(groupId)}`, session.apiContext.value);
  await loadRows();
}

onMounted(loadRows);
</script>
