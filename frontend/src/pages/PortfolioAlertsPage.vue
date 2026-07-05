<template>
  <section>
    <PageHeader
      :eyebrow="t('portfolio.eyebrow')"
      :title="t('portfolio.alertsTitle')"
      :description="t('portfolio.alertsDescription')"
    >
      <template #actions>
        <Button icon="pi pi-plus" :label="t('common.addRule')" :disabled="!canWrite" @click="openCreate" />
      </template>
    </PageHeader>

    <PortfolioSubnav />
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <MetricGrid :items="metrics" />

    <DataTable :value="rules" size="small" class="uno-rounded-xl uno-border uno-border-[#dce7e7] uno-bg-white">
      <Column field="ticker" :header="t('common.ticker')" />
      <Column field="company_name" :header="t('common.companyName')">
        <template #body="{ data }">
          {{ data.company_name || t('common.na') }}
        </template>
      </Column>
      <Column field="field" :header="t('common.field')" />
      <Column field="value" :header="t('common.value')" />
      <Column :header="t('common.created')">
        <template #body="{ data }">
          {{ formatDateTime(data.created_at) }}
        </template>
      </Column>
      <Column v-if="canWrite" :header="t('common.actions')">
        <template #body="{ data }">
          <div class="uno-flex uno-gap-2">
            <Button icon="pi pi-pencil" text severity="secondary" @click="openEdit(data)" />
            <Button
              :data-testid="`alert-delete-${data.id}`"
              icon="pi pi-trash"
              text
              severity="danger"
              @click="removeRule(String(data.id))"
            />
          </div>
        </template>
      </Column>
    </DataTable>

    <Card class="uno-mt-4">
      <template #title>{{ t('portfolio.activeHits') }}</template>
      <template #content>
        <DataTable :value="hits" size="small">
          <Column field="ticker" :header="t('common.ticker')" />
          <Column field="company_name" :header="t('common.companyName')">
            <template #body="{ data }">
              {{ data.company_name || t('common.na') }}
            </template>
          </Column>
          <Column field="field" :header="t('common.field')" />
          <Column field="expected_value" :header="t('common.value')" />
          <Column field="actual_value" :header="t('common.signal')" />
          <Column field="run_id" :header="t('common.runId')" />
          <Column field="run_date" :header="t('common.date')" />
        </DataTable>
      </template>
    </Card>

    <AlertDialog v-model:visible="dialogOpen" :mode="dialogMode" :rule="activeRule" @saved="loadRows" />
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import Message from 'primevue/message';
import { computed, onMounted, ref } from 'vue';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import AlertDialog from '../components/portfolio/AlertDialog.vue';
import PortfolioSubnav from '../components/portfolio/PortfolioSubnav.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, formatDateTime, type JsonRecord } from '../utils/format';

const session = useSession();
const canWrite = computed(() => session.canWrite.value);
const { t } = useI18n();
const payload = ref<JsonRecord | null>(null);
const error = ref('');
const dialogOpen = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const activeRule = ref<JsonRecord | null>(null);

const rules = computed(() => asArray<JsonRecord>(payload.value?.rules));
const hits = computed(() => asArray<JsonRecord>(payload.value?.hits));
const metrics = computed(() => [
  { label: t('portfolio.alertRules'), value: rules.value.length },
  { label: t('portfolio.activeHits'), value: hits.value.length },
]);

async function loadRows() {
  error.value = '';
  try {
    payload.value = await apiGet<JsonRecord>('/api/alerts', session.apiContext.value);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('portfolio.loadError');
  }
}

function openCreate() {
  dialogMode.value = 'create';
  activeRule.value = null;
  dialogOpen.value = true;
}

function openEdit(rule: JsonRecord) {
  dialogMode.value = 'edit';
  activeRule.value = rule;
  dialogOpen.value = true;
}

async function removeRule(ruleId: string) {
  await apiDelete(`/api/alerts/rules/${encodeURIComponent(ruleId)}`, session.apiContext.value);
  await loadRows();
}

onMounted(loadRows);
</script>
