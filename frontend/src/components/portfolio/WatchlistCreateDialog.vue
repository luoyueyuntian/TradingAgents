<template>
  <PortfolioDialog
    :visible="visible"
    :title="t('common.watchlist')"
    :save-label="t('common.add')"
    :cancel-label="t('common.cancel')"
    :loading="saving"
    :disabled="!selectedStock"
    :error="error"
    @update:visible="emit('update:visible', $event)"
    @submit="save"
  >
    <PortfolioStockPicker v-model:selectedStock="selectedStock" v-model:stockMarket="stockMarket" :disabled="saving" />
  </PortfolioDialog>
</template>

<script setup lang="ts">
import { ref } from 'vue';

import { useI18n } from '../../i18n';
import type { StockCatalogOption } from '../../pages/analyzeStockSelection';
import { apiPost } from '../../services/api';
import { useSession } from '../../stores/session';
import PortfolioDialog from './PortfolioDialog.vue';
import PortfolioStockPicker from './PortfolioStockPicker.vue';

defineProps<{ visible: boolean }>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'saved'): void;
}>();

const session = useSession();
const { t } = useI18n();
const stockMarket = ref('us');
const selectedStock = ref<Required<StockCatalogOption> | null>(null);
const saving = ref(false);
const error = ref('');

async function save() {
  if (!selectedStock.value) {
    return;
  }
  saving.value = true;
  error.value = '';
  try {
    await apiPost('/api/watchlist', { ticker: selectedStock.value.symbol }, session.apiContext.value);
    selectedStock.value = null;
    emit('saved');
    emit('update:visible', false);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('portfolio.loadError');
  } finally {
    saving.value = false;
  }
}
</script>
