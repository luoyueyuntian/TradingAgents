<template>
  <section>
    <PageHeader
      :eyebrow="t('portfolio.eyebrow')"
      :title="t('portfolio.stockGroups')"
      :description="t('nav.portfolioDesc')"
    >
      <template #actions>
        <Button icon="pi pi-plus" :label="t('common.add')" :disabled="!canWrite" @click="openCreate" />
      </template>
    </PageHeader>

    <PortfolioSubnav />
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <MetricGrid :items="metrics" />

    <div class="uno-grid uno-gap-3">
      <div
        v-for="group in groups"
        :key="group.id"
        class="uno-rounded-xl uno-border uno-border-[#dce7e7] uno-bg-white uno-p-4"
      >
        <div class="uno-flex uno-items-center uno-justify-between">
          <div>
            <div class="uno-font-800 uno-text-[#14363a]">{{ group.name }}</div>
            <div class="uno-text-sm uno-text-[#5f7376]">{{ asArray(group.tickers).join(', ') }}</div>
          </div>
          <div class="uno-flex uno-gap-2">
            <Button v-if="canWrite" icon="pi pi-pencil" text severity="secondary" @click="openEdit(group)" />
            <Button
              v-if="canWrite"
              :data-testid="`stock-group-delete-${group.id}`"
              icon="pi pi-trash"
              text
              severity="danger"
              @click="removeGroup(String(group.id))"
            />
          </div>
        </div>
      </div>
    </div>

    <StockGroupDialog v-model:visible="dialogOpen" :mode="dialogMode" :group="activeGroup" @saved="loadRows" />
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Message from 'primevue/message';
import { computed, onMounted, ref } from 'vue';

import MetricGrid from '../components/MetricGrid.vue';
import PageHeader from '../components/PageHeader.vue';
import PortfolioSubnav from '../components/portfolio/PortfolioSubnav.vue';
import StockGroupDialog from '../components/portfolio/StockGroupDialog.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, type JsonRecord } from '../utils/format';

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
