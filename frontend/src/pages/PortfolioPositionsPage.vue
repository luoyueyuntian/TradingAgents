<template>
  <section>
    <PageHeader
      :eyebrow="t('portfolio.eyebrow')"
      :title="t('portfolio.positions')"
      :description="t('nav.portfolioDesc')"
    >
      <template #actions>
        <Button icon="pi pi-plus" :label="t('common.addPosition')" :disabled="!canWrite" @click="openCreate" />
      </template>
    </PageHeader>

    <PortfolioSubnav />
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <MetricGrid :items="metrics" />

    <div class="uno-grid uno-gap-3">
      <div
        v-for="item in positions"
        :key="item.id"
        class="uno-rounded-xl uno-border uno-border-[#dce7e7] uno-bg-white uno-p-4"
      >
        <div class="uno-flex uno-items-center uno-justify-between">
          <div>
            <div class="uno-font-800 uno-text-[#14363a]">{{ item.ticker }}</div>
            <div class="uno-text-sm uno-text-[#5f7376]">{{ item.quantity }} @ {{ item.average_cost }}</div>
          </div>
          <div class="uno-flex uno-items-center uno-gap-2">
            <Tag :value="item.latest_signal || t('common.na')" />
            <Button v-if="canWrite" icon="pi pi-pencil" text severity="secondary" @click="openEdit(item)" />
            <Button
              v-if="canWrite"
              :data-testid="`position-delete-${item.id}`"
              icon="pi pi-trash"
              text
              severity="danger"
              @click="removePosition(String(item.id))"
            />
          </div>
        </div>
      </div>
    </div>

    <PositionDialog v-model:visible="dialogOpen" :mode="dialogMode" :position="activePosition" @saved="loadRows" />
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
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
import { asArray, type JsonRecord } from '../utils/format';

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
  { label: t('dashboard.metricPortfolio'), value: Number(payload.value?.summary?.total_cost_basis || 0) },
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
