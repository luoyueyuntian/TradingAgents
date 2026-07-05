<template>
  <section>
    <PageHeader
      :eyebrow="t('portfolio.eyebrow')"
      :title="t('common.watchlist')"
      :description="t('nav.portfolioDesc')"
    >
      <template #actions>
        <Button icon="pi pi-plus" :label="t('common.add')" :disabled="!canWrite" @click="dialogOpen = true" />
      </template>
    </PageHeader>

    <PortfolioSubnav />
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <MetricGrid :items="metrics" />

    <div class="uno-grid uno-gap-3">
      <div
        v-for="item in rows"
        :key="item.ticker"
        class="uno-rounded-xl uno-border uno-border-[#dce7e7] uno-bg-white uno-p-4"
      >
        <div class="uno-flex uno-items-center uno-justify-between">
          <div>
            <div class="uno-font-800 uno-text-[#14363a]">{{ item.ticker }}</div>
            <div class="uno-text-sm uno-text-[#5f7376]">{{ item.latest_date || t('portfolio.noSavedRun') }}</div>
          </div>
          <div class="uno-flex uno-items-center uno-gap-2">
            <Tag :value="item.latest_signal || item.latest_status || t('common.saved')" />
            <Button
              v-if="canWrite"
              :data-testid="`watchlist-delete-${item.ticker}`"
              icon="pi pi-trash"
              severity="danger"
              text
              @click="removeTicker(item.ticker)"
            />
          </div>
        </div>
      </div>
    </div>

    <WatchlistCreateDialog v-model:visible="dialogOpen" @saved="loadRows" />
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
import WatchlistCreateDialog from '../components/portfolio/WatchlistCreateDialog.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet } from '../services/api';
import { useSession } from '../stores/session';
import type { JsonRecord } from '../utils/format';

const session = useSession();
const canWrite = computed(() => session.canWrite.value);
const { t } = useI18n();
const rows = ref<JsonRecord[]>([]);
const error = ref('');
const dialogOpen = ref(false);

const metrics = computed(() => [
  { label: t('common.watchlist'), value: rows.value.length },
]);

async function loadRows() {
  error.value = '';
  try {
    rows.value = await apiGet<JsonRecord[]>('/api/watchlist', session.apiContext.value);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('portfolio.loadError');
  }
}

async function removeTicker(ticker: string) {
  await apiDelete(`/api/watchlist/${encodeURIComponent(ticker)}`, session.apiContext.value);
  await loadRows();
}

onMounted(loadRows);
</script>
