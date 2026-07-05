<template>
  <PortfolioDialog
    :visible="visible"
    :title="mode === 'edit' ? t('common.save') : t('common.addPosition')"
    :save-label="mode === 'edit' ? t('common.save') : t('common.add')"
    :cancel-label="t('common.cancel')"
    :loading="saving"
    :disabled="saveDisabled"
    :error="error"
    @update:visible="emit('update:visible', $event)"
    @submit="save"
  >
    <PortfolioStockPicker
      v-if="mode === 'create'"
      v-model:selectedStock="selectedStock"
      v-model:stockMarket="stockMarket"
      :disabled="saving"
    />
    <div v-else class="uno-font-700 uno-text-[#14363a]">{{ currentTicker }}</div>

    <label class="uno-grid uno-gap-1">
      <span class="uno-text-[#6f8183]">{{ t('portfolio.quantity') }}</span>
      <InputText v-model="quantity" type="number" />
    </label>

    <label class="uno-grid uno-gap-1">
      <span class="uno-text-[#6f8183]">{{ t('portfolio.averageCost') }}</span>
      <InputText v-model="averageCost" type="number" />
    </label>
  </PortfolioDialog>
</template>

<script setup lang="ts">
import InputText from 'primevue/inputtext';
import { computed, ref, watch } from 'vue';

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
  position?: JsonRecord | null;
}>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'saved'): void;
}>();

const session = useSession();
const { t } = useI18n();
const stockMarket = ref('us');
const selectedStock = ref<Required<StockCatalogOption> | null>(null);
const quantity = ref('');
const averageCost = ref('');
const saving = ref(false);
const error = ref('');

const currentTicker = computed(() => String(props.position?.ticker || selectedStock.value?.symbol || ''));
const saveDisabled = computed(() => (
  !currentTicker.value || Number(quantity.value || 0) <= 0 || Number(averageCost.value || 0) < 0
));

watch(
  () => props.position,
  (value) => {
    quantity.value = value ? String(value.quantity ?? '') : '';
    averageCost.value = value ? String(value.average_cost ?? '') : '';
  },
  { immediate: true },
);

async function save() {
  saving.value = true;
  error.value = '';
  try {
    if (props.mode === 'edit' && props.position?.id) {
      await apiPatch(
        `/api/portfolio/positions/${encodeURIComponent(String(props.position.id))}`,
        {
          quantity: Number(quantity.value),
          average_cost: Number(averageCost.value),
        },
        session.apiContext.value,
      );
    } else {
      await apiPost(
        '/api/portfolio/positions',
        {
          ticker: currentTicker.value,
          quantity: Number(quantity.value),
          average_cost: Number(averageCost.value),
        },
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
