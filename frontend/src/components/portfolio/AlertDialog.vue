<template>
  <PortfolioDialog
    :visible="visible"
    :title="mode === 'edit' ? t('portfolio.editAlert') : t('portfolio.addAlertTitle')"
    :save-label="mode === 'edit' ? t('common.save') : t('common.addRule')"
    :cancel-label="t('common.cancel')"
    :loading="saving"
    :disabled="!field || !value.trim() || (!currentTicker && mode === 'create')"
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

    <Select v-model="field" :options="fieldOptions" option-label="label" option-value="value" />
    <InputText v-model="value" :placeholder="t('portfolio.valuePlaceholder')" />
  </PortfolioDialog>
</template>

<script setup lang="ts">
import InputText from 'primevue/inputtext';
import Select from 'primevue/select';
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
  rule?: JsonRecord | null;
}>();

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'saved'): void;
}>();

const session = useSession();
const { t } = useI18n();
const stockMarket = ref('us');
const selectedStock = ref<Required<StockCatalogOption> | null>(null);
const field = ref<'signal' | 'status'>('signal');
const value = ref('');
const saving = ref(false);
const error = ref('');

const fieldOptions = computed(() => [
  { label: t('common.signal'), value: 'signal' },
  { label: t('common.status'), value: 'status' },
]);
const currentTicker = computed(() => String(props.rule?.ticker || selectedStock.value?.symbol || ''));

watch(
  () => props.rule,
  (rule) => {
    field.value = rule?.field === 'status' ? 'status' : 'signal';
    value.value = String(rule?.value || '');
  },
  { immediate: true },
);

async function save() {
  saving.value = true;
  error.value = '';
  try {
    if (props.mode === 'edit' && props.rule?.id) {
      await apiPatch(
        `/api/alerts/rules/${encodeURIComponent(String(props.rule.id))}`,
        { field: field.value, value: value.value.trim() },
        session.apiContext.value,
      );
    } else {
      await apiPost(
        '/api/alerts/rules',
        { ticker: currentTicker.value, field: field.value, value: value.value.trim() },
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
