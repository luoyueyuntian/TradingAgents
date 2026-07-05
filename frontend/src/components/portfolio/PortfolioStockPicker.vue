<template>
  <div class="uno-grid uno-gap-3">
    <label class="uno-grid uno-gap-1">
      <span class="uno-text-[#6f8183]">{{ t('analysis.stockMarket') }}</span>
      <Select
        v-model="stockMarket"
        :options="marketOptions"
        option-label="label"
        option-value="value"
        :disabled="disabled"
        @change="handleMarketChange"
      />
    </label>

    <label class="uno-grid uno-gap-1">
      <span class="uno-text-[#6f8183]">{{ t('common.ticker') }}</span>
      <AutoComplete
        v-model="selectedStock"
        :suggestions="stockOptions"
        option-label="label"
        :placeholder="t('analysis.stockPlaceholder')"
        :loading="loading"
        dropdown
        complete-on-focus
        force-selection
        show-clear
        :disabled="disabled"
        @complete="onComplete"
        @clear="clearSelection"
      >
        <template #option="{ option }">
          <div class="uno-grid uno-gap-0.5">
            <strong>{{ option.symbol }}</strong>
            <small class="uno-text-[#6f8183]">{{ [option.name, option.exchange].filter(Boolean).join(' · ') }}</small>
          </div>
        </template>
      </AutoComplete>
    </label>
  </div>
</template>

<script setup lang="ts">
import AutoComplete from 'primevue/autocomplete';
import Select from 'primevue/select';
import { computed, onMounted, ref } from 'vue';

import { useI18n } from '../../i18n';
import {
  buildStockSearchPath,
  normalizeStockOptions,
  type StockCatalogOption,
  type StockMarketOption,
} from '../../pages/analyzeStockSelection';
import { apiGet } from '../../services/api';
import { useSession } from '../../stores/session';

const selectedStock = defineModel<Required<StockCatalogOption> | null>('selectedStock', { default: null });
const stockMarket = defineModel<string>('stockMarket', { default: 'us' });

withDefaults(defineProps<{ disabled?: boolean }>(), {
  disabled: false,
});

const session = useSession();
const { t } = useI18n();
const markets = ref<StockMarketOption[]>([]);
const stocks = ref<Required<StockCatalogOption>[]>([]);
const loading = ref(false);

const marketOptions = computed(() => (
  markets.value.length
    ? markets.value
    : [
        { value: 'us', label: t('analysis.usStocks') },
        { value: 'hk', label: t('analysis.hkStocks') },
        { value: 'cn_a', label: t('analysis.cnAStocks') },
      ]
));

const stockOptions = computed(() => stocks.value);

async function loadMarkets() {
  markets.value = await apiGet<StockMarketOption[]>('/api/stocks/markets', session.apiContext.value);
}

async function loadStocks(query = '') {
  loading.value = true;
  try {
    const rows = await apiGet<StockCatalogOption[]>(
      buildStockSearchPath(stockMarket.value, query, 100),
      session.apiContext.value,
    );
    stocks.value = normalizeStockOptions(rows);
  } finally {
    loading.value = false;
  }
}

async function handleMarketChange() {
  selectedStock.value = null;
  await loadStocks();
}

async function onComplete(event: { query?: string }) {
  await loadStocks(event.query || '');
}

function clearSelection() {
  selectedStock.value = null;
}

onMounted(async () => {
  await loadMarkets();
  await loadStocks();
});
</script>
