<template>
  <section>
    <PageHeader
      :eyebrow="t('automations.eyebrow')"
      :title="t('automations.title')"
      :description="t('automations.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="loadRules" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div class="content-grid">
      <Card>
        <template #title>{{ t('automations.createRule') }}</template>
        <template #content>
          <div class="form-grid">
            <InputText v-model="form.name" :placeholder="t('automations.namePlaceholder')" />
            <Select v-model="form.source" :options="sourceOptions" option-label="label" option-value="value" />
            <Select v-model="form.cadence" :options="cadenceOptions" option-label="label" option-value="value" />
            <Select v-model="form.weekday" :options="weekdayOptions" option-label="label" option-value="value" :disabled="form.cadence !== 'weekly'" />
            <InputText v-model="form.time" type="time" />
          </div>
          <Textarea
            v-model="form.tickers"
            rows="3"
            auto-resize
            :placeholder="t('automations.manualTickersPlaceholder')"
            style="width: 100%; margin-top: 0.75rem;"
          />
          <div class="actions-row" style="margin-top: 0.75rem;">
            <label class="inline-row">
              <input v-model="form.enabled" type="checkbox">
              <span>{{ t('common.enabled') }}</span>
            </label>
            <Button icon="pi pi-save" :label="t('automations.saveAutomation')" @click="saveRule" />
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('automations.rules') }}</template>
        <template #content>
          <div class="list-stack">
            <div v-for="rule in rules" :key="rule.id" class="list-item">
              <div class="list-item-title">
                <span>{{ rule.name }}</span>
                <Tag :value="rule.enabled ? t('common.enabled') : t('common.paused')" :severity="rule.enabled ? 'success' : 'warn'" />
              </div>
              <small class="muted">{{ rule.source }} · {{ rule.cadence }} · {{ rule.time_of_day || t('common.na') }} · {{ t('automations.nextRun', { time: rule.next_run_at || t('common.na') }) }}</small>
              <div class="actions-row" style="margin-top: 0.6rem;">
                <Button icon="pi pi-bolt" :label="t('automations.runNow')" severity="secondary" @click="runNow(rule.id)" />
                <Button :icon="rule.enabled ? 'pi pi-pause' : 'pi pi-play'" :label="rule.enabled ? t('common.pause') : t('common.enable')" severity="secondary" @click="toggleRule(rule)" />
                <Button icon="pi pi-trash" :label="t('common.delete')" severity="danger" outlined @click="deleteRule(rule.id)" />
              </div>
            </div>
          </div>
          <p v-if="!rules.length" class="muted">{{ t('automations.noRules') }}</p>
        </template>
      </Card>
    </div>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
import Textarea from 'primevue/textarea';
import { computed, onMounted, reactive, ref } from 'vue';

import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPatch, apiPost } from '../services/api';
import { useSession } from '../stores/session';
import type { JsonRecord } from '../utils/format';
import { buildAutomationPayload } from './automationPayload';

const session = useSession();
const rules = ref<JsonRecord[]>([]);
const error = ref('');
const { t } = useI18n();
const form = reactive({
  name: '',
  source: 'watchlist',
  cadence: 'daily',
  weekday: 'fri',
  time: '09:00',
  tickers: '',
  enabled: true,
});
const sourceOptions = computed(() => [
  { label: t('automations.sourceWatchlist'), value: 'watchlist' },
  { label: t('automations.sourceManual'), value: 'manual' },
]);
const cadenceOptions = computed(() => [
  { label: t('automations.daily'), value: 'daily' },
  { label: t('automations.weekly'), value: 'weekly' },
]);
const weekdayOptions = computed(() => [
  { label: t('automations.monday'), value: 'mon' },
  { label: t('automations.tuesday'), value: 'tue' },
  { label: t('automations.wednesday'), value: 'wed' },
  { label: t('automations.thursday'), value: 'thu' },
  { label: t('automations.friday'), value: 'fri' },
  { label: t('automations.saturday'), value: 'sat' },
  { label: t('automations.sunday'), value: 'sun' },
]);

async function loadRules() {
  error.value = '';
  try {
    rules.value = await apiGet<JsonRecord[]>('/api/automations', session.apiContext.value);
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('automations.loadError');
  }
}

async function saveRule() {
  if (!form.name.trim()) return;
  await apiPost('/api/automations', buildAutomationPayload(form), session.apiContext.value);
  Object.assign(form, { name: '', source: 'watchlist', cadence: 'daily', weekday: 'fri', time: '09:00', tickers: '', enabled: true });
  await loadRules();
}

async function toggleRule(rule: JsonRecord) {
  await apiPatch(`/api/automations/${encodeURIComponent(String(rule.id))}`, {
    enabled: !rule.enabled,
  }, session.apiContext.value);
  await loadRules();
}

async function runNow(ruleId: string) {
  await apiPost(`/api/automations/${encodeURIComponent(ruleId)}/run-now`, {}, session.apiContext.value);
  await loadRules();
}

async function deleteRule(ruleId: string) {
  await apiDelete(`/api/automations/${encodeURIComponent(ruleId)}`, session.apiContext.value);
  await loadRules();
}

onMounted(loadRules);
</script>
