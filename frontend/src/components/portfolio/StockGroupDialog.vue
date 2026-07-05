<template>
  <PortfolioDialog
    :visible="visible"
    :title="mode === 'edit' ? t('portfolio.editStockGroup') : t('portfolio.addStockGroup')"
    :save-label="mode === 'edit' ? t('common.save') : t('common.add')"
    :cancel-label="t('common.cancel')"
    :loading="saving"
    :disabled="!name.trim() || !tickers.length"
    :error="error"
    @update:visible="emit('update:visible', $event)"
    @submit="save"
  >
    <label class="uno-grid uno-gap-1">
      <span class="uno-text-[#6f8183]">{{ t('portfolio.stockGroupName') }}</span>
      <InputText v-model="name" />
    </label>

    <PortfolioStockPicker v-model:selectedStock="selectedStock" v-model:stockMarket="stockMarket" :disabled="saving" />
    <Button :label="t('portfolio.addTickerToGroup')" severity="secondary" :disabled="!selectedStock" @click="addSelectedTicker" />

    <div class="uno-flex uno-flex-wrap uno-gap-2">
      <span
        v-for="ticker in tickers"
        :key="ticker"
        class="uno-inline-flex uno-items-center uno-gap-2 uno-rounded-full uno-bg-[#edf4f2] uno-px-3 uno-py-1 uno-text-sm uno-font-700 uno-text-[#243a3d]"
      >
        {{ ticker }}
        <button type="button" class="uno-bg-transparent uno-p-0" @click="removeTicker(ticker)">x</button>
      </span>
    </div>
  </PortfolioDialog>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import { ref, watch } from 'vue';

import { useI18n } from '../../i18n';
import type { StockCatalogOption } from '../../pages/analyzeStockSelection';
import { apiPatch, apiPost } from '../../services/api';
import { useSession } from '../../stores/session';
import type { JsonRecord } from '../../utils/format';
import PortfolioDialog from './PortfolioDialog.vue';
import PortfolioStockPicker from './PortfolioStockPicker.vue';

const props = defineProps<{
  visible: boolean;
  mode: 'create' | 'edit';
  group?: JsonRecord | null;
}>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'saved'): void;
}>();

const session = useSession();
const { t } = useI18n();
const name = ref('');
const tickers = ref<string[]>([]);
const stockMarket = ref('us');
const selectedStock = ref<Required<StockCatalogOption> | null>(null);
const saving = ref(false);
const error = ref('');

watch(
  () => props.group,
  (value) => {
    name.value = String(value?.name || '');
    tickers.value = Array.isArray(value?.tickers) ? [...(value?.tickers as string[])] : [];
  },
  { immediate: true },
);

function addSelectedTicker() {
  const symbol = selectedStock.value?.symbol;
  if (!symbol || tickers.value.includes(symbol)) {
    return;
  }
  tickers.value = [...tickers.value, symbol];
  selectedStock.value = null;
}

function removeTicker(ticker: string) {
  tickers.value = tickers.value.filter((item) => item !== ticker);
}

async function save() {
  saving.value = true;
  error.value = '';
  try {
    if (props.mode === 'edit' && props.group?.id) {
      await apiPatch(
        `/api/stock-groups/${encodeURIComponent(String(props.group.id))}`,
        { name: name.value.trim(), tickers: tickers.value },
        session.apiContext.value,
      );
    } else {
      await apiPost(
        '/api/stock-groups',
        { name: name.value.trim(), tickers: tickers.value },
        session.apiContext.value,
      );
    }
    emit('saved');
    emit('update:visible', false);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('portfolio.loadError');
  } finally {
    saving.value = false;
  }
}
</script>
