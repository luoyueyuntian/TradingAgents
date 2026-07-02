<template>
  <section>
    <PageHeader
      :eyebrow="t('workspace.eyebrow')"
      :title="t('workspace.title')"
      :description="t('workspace.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="loadAll" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

    <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(320px,1fr))] uno-gap-4">
      <Card>
        <template #title>{{ t('workspace.searchTitle') }}</template>
        <template #content>
          <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
            <InputText v-model="searchQuery" :placeholder="t('workspace.searchPlaceholder')" @keyup.enter="runSearch" />
            <Button icon="pi pi-search" :label="t('common.search')" @click="runSearch" />
          </div>
          <div class="uno-mt-3 uno-grid uno-gap-[0.65rem]">
            <div v-for="item in asArray(searchResults?.results)" :key="`${item.kind}-${item.entity_id}`" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ item.title }}</span>
                <Tag :value="item.kind" severity="info" />
              </div>
              <small class="uno-text-[#6f8183]">{{ item.subtitle }} · {{ item.excerpt }}</small>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('workspace.notes') }}</template>
        <template #content>
          <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(220px,1fr))] uno-gap-[0.8rem]">
            <InputText v-model="note.ticker" :placeholder="t('workspace.tickerOptional')" />
            <InputText v-model="note.tags" :placeholder="t('workspace.tagsPlaceholder')" />
          </div>
          <Textarea v-model="note.content" rows="4" auto-resize :placeholder="t('workspace.notePlaceholder')" class="uno-mt-3 uno-w-full" />
          <Button icon="pi pi-save" :label="t('workspace.saveNote')" class="uno-mt-3" @click="saveNote" />
          <div class="uno-mt-3 uno-grid uno-gap-[0.65rem]">
            <div v-for="item in notes" :key="item.id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ item.ticker || item.run_id || t('workspace.workspaceFallback') }}</span>
                <small class="uno-text-[#6f8183]">{{ formatDateTime(item.updated_at) }}</small>
              </div>
              <p>{{ item.content }}</p>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('workspace.members') }}</template>
        <template #content>
          <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
            <InputText v-model="member.name" :placeholder="t('workspace.name')" />
            <Select v-model="member.role" :options="memberRoles" option-label="label" option-value="value" :placeholder="t('workspace.role')" />
            <Button icon="pi pi-user-plus" :label="t('common.add')" @click="saveMember" />
          </div>
          <div class="uno-mt-3 uno-grid uno-gap-[0.65rem]">
            <div v-for="item in members" :key="item.id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ item.name }}</span>
                <Tag :value="item.role || t('workspace.member')" severity="secondary" />
              </div>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('workspace.reviews') }}</template>
        <template #content>
          <DataTable :value="asArray(reviews?.items)" size="small">
            <Column field="run_id" :header="t('common.run')" />
            <Column field="reviewer" :header="t('workspace.reviewer')" />
            <Column field="status" :header="t('common.status')" />
            <Column field="note" :header="t('workspace.note')" />
          </DataTable>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('workspace.timeline') }}</template>
        <template #content>
          <div class="uno-grid uno-gap-[0.65rem]">
            <div v-for="event in asArray(timeline?.events).slice(0, 12)" :key="event.id || `${event.kind}-${event.occurred_at}`" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ event.title }}</span>
                <Tag :value="event.kind" />
              </div>
              <small class="uno-text-[#6f8183]">{{ formatDateTime(event.occurred_at) }} · {{ event.subtitle || event.description }}</small>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('workspace.savedViewsAndShares') }}</template>
        <template #content>
          <div class="uno-grid uno-gap-[0.65rem]">
            <div v-for="view in views" :key="view.id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ view.name }}</span>
                <Tag :value="view.group || t('workspace.view')" severity="info" />
              </div>
              <small class="uno-text-[#6f8183]">{{ view.url }}</small>
            </div>
            <div v-for="share in shares" :key="share.share_id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ t('common.publicSnapshot', { ticker: share.ticker }) }}</span>
                <a :href="share.url" target="_blank" rel="noopener">{{ t('common.open') }}</a>
              </div>
              <small class="uno-text-[#6f8183]">{{ share.share_id }} · {{ share.status }}</small>
            </div>
          </div>
        </template>
      </Card>
    </div>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import Column from 'primevue/column';
import DataTable from 'primevue/datatable';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Select from 'primevue/select';
import Tag from 'primevue/tag';
import Textarea from 'primevue/textarea';
import { computed, onMounted, reactive, ref } from 'vue';

import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiGet, apiPost } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, formatDateTime, type JsonRecord } from '../utils/format';

const session = useSession();
const searchQuery = ref('');
const searchResults = ref<JsonRecord | null>(null);
const notes = ref<JsonRecord[]>([]);
const members = ref<JsonRecord[]>([]);
const reviews = ref<JsonRecord | null>(null);
const timeline = ref<JsonRecord | null>(null);
const views = ref<JsonRecord[]>([]);
const shares = ref<JsonRecord[]>([]);
const error = ref('');
const note = reactive({ ticker: '', tags: '', content: '' });
const member = reactive({ name: '', role: '' });
const { t } = useI18n();
const memberRoles = computed(() => [
  { label: t('workspace.roleAnalyst'), value: 'analyst' },
  { label: t('workspace.roleReviewer'), value: 'reviewer' },
  { label: t('workspace.roleOperator'), value: 'operator' },
  { label: t('workspace.roleLead'), value: 'lead' },
  { label: t('workspace.roleObserver'), value: 'observer' },
]);

async function runSearch() {
  if (!searchQuery.value.trim()) {
    searchResults.value = null;
    return;
  }
  const params = new URLSearchParams({ q: searchQuery.value.trim() });
  searchResults.value = await apiGet<JsonRecord>(`/api/search?${params.toString()}`, session.apiContext.value);
}

async function loadAll() {
  error.value = '';
  try {
    const context = session.apiContext.value;
    const [noteItems, memberItems, reviewPayload, timelinePayload, viewItems, shareItems] = await Promise.all([
      apiGet<JsonRecord[]>('/api/notes', context),
      apiGet<JsonRecord[]>('/api/members', context),
      apiGet<JsonRecord>('/api/reviews', context),
      apiGet<JsonRecord>('/api/timeline', context),
      apiGet<JsonRecord[]>('/api/views', context),
      apiGet<JsonRecord[]>('/api/public-shares', context),
    ]);
    notes.value = noteItems;
    members.value = memberItems;
    reviews.value = reviewPayload;
    timeline.value = timelinePayload;
    views.value = viewItems;
    shares.value = shareItems;
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('workspace.loadError');
  }
}

async function saveNote() {
  if (!note.content.trim()) return;
  await apiPost('/api/notes', {
    content: note.content,
    ticker: note.ticker || null,
    tags: note.tags.split(',').map((tag) => tag.trim()).filter(Boolean),
  }, session.apiContext.value);
  Object.assign(note, { ticker: '', tags: '', content: '' });
  await loadAll();
}

async function saveMember() {
  if (!member.name.trim()) return;
  await apiPost('/api/members', {
    name: member.name,
    role: member.role || null,
  }, session.apiContext.value);
  Object.assign(member, { name: '', role: '' });
  await loadAll();
}

onMounted(loadAll);
</script>
