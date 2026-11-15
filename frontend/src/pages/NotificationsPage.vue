<template>
  <section>
    <PageHeader :eyebrow="t('messages.eyebrow')" :title="t('messages.title')" :description="t('messages.description')">
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" :loading="loading" @click="load" />
        <Button icon="pi pi-check" :label="t('messages.readAll')" :loading="saving" :disabled="!canWrite || saving || loading || !!error || !feed.unread_count" @click="markAll" />
      </template>
    </PageHeader>
    <Message v-if="error" severity="error" :closable="false" role="alert">{{ error }}</Message>
    <Message v-if="notice" severity="success" :closable="false" role="status">{{ notice }}</Message>
    <Card class="messages-card">
      <template #content>
        <div class="uno-mb-3 uno-flex uno-flex-wrap uno-items-center uno-gap-x-4 uno-gap-y-2">
          <label class="uno-flex uno-items-center uno-gap-2 uno-text-xs">
            {{ t('messages.kind') }}
            <Select v-model="kind" :options="kindOptions" option-label="label" option-value="value" :disabled="saving" size="small" />
          </label>
          <label class="uno-flex uno-items-center uno-gap-2 uno-text-xs">
            {{ t('messages.level') }}
            <Select v-model="severity" :options="severityOptions" option-label="label" option-value="value" :disabled="saving" size="small" />
          </label>
          <label class="uno-flex uno-items-center uno-gap-2 uno-text-sm"><input v-model="unreadOnly" type="checkbox" :disabled="saving">{{ t('messages.unreadOnly') }}</label>
          <span v-if="!loading && !error" class="uno-text-sm uno-text-[#737373]">{{ t('messages.unreadTotal', { count: feed.unread_count }) }}</span>
        </div>
        <p v-if="loading" role="status" class="uno-py-8 uno-text-center uno-text-[#737373]">{{ t('messages.loading') }}</p>
        <p v-else-if="!error && !feed.items.length" role="status" class="uno-py-8 uno-text-center uno-text-[#737373]">{{ t('messages.empty') }}</p>
        <ul v-else class="notification-list">
          <li v-for="item in feed.items" :key="item.id" class="notification-row" :class="item.is_read ? 'uno-bg-[#fafafa]' : 'uno-bg-white'">
            <div class="uno-min-w-0">
              <div class="notification-heading">
                <span v-if="!item.is_read" class="uno-h-1.5 uno-w-1.5 uno-shrink-0 uno-rounded-full uno-bg-[#b94328]" :aria-label="t('messages.unread')" />
                <strong class="notification-title" :class="item.is_read ? 'uno-font-medium' : 'uno-font-semibold'">{{ item.title }}</strong>
                <Tag class="notification-tag" :value="severityLabel(item.severity)" :severity="tagSeverity(item.severity)" />
                <div class="notification-meta">
                  <time>{{ formatDateTime(item.created_at) }}</time>
                  <span>{{ item.is_read ? t('messages.read') : t('messages.unread') }}</span>
                </div>
              </div>
              <div class="notification-description">
                <span class="notification-kind">{{ kindLabel(item.kind) }}</span>
                <p>{{ item.message }}</p>
              </div>
            </div>
            <div class="notification-actions">
              <button v-if="!item.is_read && canWrite" type="button" :disabled="saving" @click="markOne(item)">{{ t('messages.markRead') }}</button>
              <RouterLink v-if="item.run_id" :to="`/runs/${encodeURIComponent(item.run_id)}`" @click="markOne(item, false)">{{ t('messages.details') }}</RouterLink>
            </div>
          </li>
        </ul>
        <div v-if="!loading && !error" class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-2 uno-pt-2">
          <span class="uno-text-sm uno-text-[#737373]">{{ t('messages.pageSummary', { page: Math.floor(offset / pageSize) + 1, count: feed.filtered_count }) }}</span>
          <div class="uno-flex uno-gap-2">
            <Button :label="t('messages.previous')" size="small" severity="secondary" :disabled="loading || saving || offset === 0" @click="changePage(-1)" />
            <Button :label="t('messages.next')" size="small" severity="secondary" :disabled="loading || saving || offset + pageSize >= feed.filtered_count" @click="changePage(1)" />
          </div>
        </div>
      </template>
    </Card>
  </section>
</template>
<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import Message from 'primevue/message';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
import { computed, onMounted, ref, watch } from 'vue';
import { RouterLink } from 'vue-router';
import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiGet, apiPost } from '../services/api';
import { refreshUnread } from '../stores/notifications';
import { useSession } from '../stores/session';
import { formatDateTime, type JsonRecord } from '../utils/format';
const { t } = useI18n();
const session = useSession();
const canWrite = computed(() => session.canWrite.value);
const pageSize = 20;
const offset = ref(0);
const kind = ref('all');
const severity = ref('all');
const unreadOnly = ref(false);
const feed = ref<{ items: JsonRecord[]; unread_count: number; filtered_count: number }>({ items: [], unread_count: 0, filtered_count: 0 });
const loading = ref(false);
const saving = ref(false);
const error = ref('');
const notice = ref('');
let generation = 0;
let mutationGeneration = 0;
const kindOptions = computed(() => [
  { value: 'all', label: t('messages.allKinds') }, { value: 'run', label: t('messages.run') },
  { value: 'alert', label: t('messages.alert') }, { value: 'action', label: t('messages.action') },
  { value: 'comment', label: t('messages.comment') }, { value: 'review', label: t('messages.review') },
]);
const severityOptions = computed(() => [
  { value: 'all', label: t('messages.allLevels') }, { value: 'info', label: t('messages.info') },
  { value: 'warning', label: t('messages.warning') }, { value: 'error', label: t('messages.error') },
]);
function kindLabel(value: string) { return kindOptions.value.find((item) => item.value === value)?.label || value; }
function severityLabel(value: string) { return severityOptions.value.find((item) => item.value === value)?.label || value; }
function tagSeverity(value: string) { return value === 'error' ? 'danger' : value === 'warning' ? 'warn' : 'info'; }
function filters() {
  const params = new URLSearchParams();
  if (kind.value !== 'all') params.set('kind', kind.value);
  if (severity.value !== 'all') params.set('severity', severity.value);
  if (unreadOnly.value) params.set('unread_only', 'true');
  return params;
}
async function load() {
  const requestId = ++generation;
  const context = { ...session.apiContext.value };
  loading.value = true; error.value = '';
  feed.value = { ...feed.value, items: [] };
  try {
    const params = filters(); params.set('offset', String(offset.value)); params.set('limit', String(pageSize));
    const result = await apiGet<typeof feed.value>(`/api/notifications?${params}`, context);
    if (requestId !== generation || context.tenantId !== session.apiContext.value.tenantId) return;
    feed.value = result;
    if (offset.value > 0 && offset.value >= result.filtered_count) {
      offset.value = Math.max(0, Math.floor((result.filtered_count - 1) / pageSize) * pageSize);
      await load(); return;
    }
    await refreshUnread(context);
  } catch (exc) {
    if (requestId === generation) error.value = t('messages.loadError') + (exc instanceof Error ? ' ' + exc.message : '');
  } finally { if (requestId === generation) loading.value = false; }
}
async function readAction(path: string, reload: boolean) {
  if (saving.value || !canWrite.value) return;
  const context = { ...session.apiContext.value };
  const mutationId = ++mutationGeneration;
  saving.value = true; error.value = ''; notice.value = '';
  try {
    await apiPost(path, {}, context);
    if (mutationId !== mutationGeneration || context.tenantId !== session.apiContext.value.tenantId) return;
    await refreshUnread(context);
    if (mutationId !== mutationGeneration || context.tenantId !== session.apiContext.value.tenantId) return;
    if (reload) {
      await load();
      if (mutationId === mutationGeneration && context.tenantId === session.apiContext.value.tenantId && !error.value) notice.value = t('messages.readSaved');
    }
  } catch (exc) {
    if (mutationId === mutationGeneration && context.tenantId === session.apiContext.value.tenantId) {
      error.value = t('messages.readError') + (exc instanceof Error ? ' ' + exc.message : '');
    }
  } finally { if (mutationId === mutationGeneration) saving.value = false; }
}
function markOne(item: JsonRecord, reload = true) { if (!item.is_read) return readAction(`/api/notifications/${encodeURIComponent(item.id)}/read`, reload); }
function markAll() { return readAction(`/api/notifications/read-all?${filters()}`, true); }
function changePage(direction: number) { offset.value = Math.max(0, offset.value + direction * pageSize); notice.value = ''; void load(); }
watch([kind, severity, unreadOnly], () => { offset.value = 0; notice.value = ''; void load(); });
watch(() => session.apiContext.value.tenantId, () => { mutationGeneration++; saving.value = false; generation++; feed.value = { items: [], unread_count: 0, filtered_count: 0 }; offset.value = 0; notice.value = ''; void load(); });
onMounted(load);
</script>

<style scoped>
.messages-card :deep(.p-card-body) { padding: 12px; }
.messages-card :deep(.p-card-content) { padding: 0; }
.notification-list { margin: 0; padding: 0; list-style: none; border: 1px solid #e5e5e5; border-radius: 8px; overflow: hidden; }
.notification-row { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; padding: 10px 12px; border-bottom: 1px solid #e5e5e5; }
.notification-row:last-child { border-bottom: 0; }
.notification-heading { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 7px; }
.notification-title { font-size: 13px; line-height: 20px; overflow-wrap: anywhere; }
.notification-tag { font-size: 10px; padding: 1px 5px; }
.notification-meta { display: flex; flex-wrap: wrap; gap: 8px; margin-left: auto; color: var(--p-text-muted-color); font-size: 11px; line-height: 18px; }
.notification-description { display: flex; align-items: baseline; gap: 8px; margin-top: 3px; color: var(--p-text-muted-color); font-size: 12px; line-height: 18px; }
.notification-kind { flex-shrink: 0; }
.notification-description p { min-width: 0; margin: 0; white-space: pre-wrap; overflow-wrap: anywhere; }
.notification-actions { display: flex; align-items: flex-start; gap: 12px; font-size: 12px; line-height: 20px; }
.notification-actions button, .notification-actions a { display: inline-flex; align-items: center; min-height: 28px; padding: 3px 0; border: 0; background: transparent; font: inherit; color: var(--p-primary-color); text-decoration: none; white-space: nowrap; cursor: pointer; }
.notification-actions a { color: var(--p-blue-600); }
.notification-actions button:hover, .notification-actions a:hover { text-decoration: underline; }
.notification-actions button:disabled { opacity: 0.5; cursor: default; }
.notification-actions button:focus-visible, .notification-actions a:focus-visible { outline: 2px solid var(--p-primary-color); outline-offset: 2px; }
@media (max-width: 700px) {
  .notification-row { grid-template-columns: minmax(0, 1fr); gap: 3px; padding: 10px; }
  .notification-meta { margin-left: 0; }
  .notification-actions { justify-content: flex-end; gap: 16px; }
  .notification-actions button, .notification-actions a { min-height: 32px; }
}
</style>
