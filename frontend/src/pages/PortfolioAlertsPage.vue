<template>
  <section>
    <PageHeader
      :eyebrow="t('portfolio.eyebrow')"
      :title="t('portfolio.alerts')"
      :description="t('nav.portfolioDesc')"
    >
      <template #actions>
        <Button icon="pi pi-plus" :label="t('common.addRule')" :disabled="!canWrite" @click="openCreate" />
      </template>
    </PageHeader>

    <PortfolioSubnav />
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <MetricGrid :items="metrics" />

    <div class="uno-grid uno-gap-3">
      <div
        v-for="rule in rules"
        :key="rule.id"
        class="uno-rounded-xl uno-border uno-border-[#dce7e7] uno-bg-white uno-p-4"
      >
        <div class="uno-flex uno-items-center uno-justify-between">
          <div>
            <div class="uno-font-800 uno-text-[#14363a]">{{ rule.ticker }}</div>
            <div class="uno-text-sm uno-text-[#5f7376]">{{ rule.field }} = {{ rule.value }}</div>
          </div>
          <div class="uno-flex uno-gap-2">
            <Button v-if="canWrite" icon="pi pi-pencil" text severity="secondary" @click="openEdit(rule)" />
            <Button
              v-if="canWrite"
              :data-testid="`alert-delete-${rule.id}`"
              icon="pi pi-trash"
              text
              severity="danger"
              @click="removeRule(String(rule.id))"
            />
          </div>
        </div>
      </div>
    </div>

    <AlertDialog v-model:visible="dialogOpen" :mode="dialogMode" :rule="activeRule" @saved="loadRows" />
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Message from 'primevue/message';
import { computed, onMounted, ref } from 'vue';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import AlertDialog from '../components/portfolio/AlertDialog.vue';
import PortfolioSubnav from '../components/portfolio/PortfolioSubnav.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, type JsonRecord } from '../utils/format';

const session = useSession();
const canWrite = computed(() => session.canWrite.value);
const { t } = useI18n();
const payload = ref<JsonRecord | null>(null);
const error = ref('');
const dialogOpen = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const activeRule = ref<JsonRecord | null>(null);

const rules = computed(() => asArray<JsonRecord>(payload.value?.rules));
const metrics = computed(() => [
  { label: t('portfolio.alertRules'), value: rules.value.length },
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
