<template>
  <section>
    <PageHeader
      :eyebrow="t('workspace.eyebrow')"
      :title="t('workspace.title')"
      :description="t('workspace.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" @click="loadAll" />
        <Button icon="pi pi-download" :label="t('workspace.exportJson')" severity="secondary" @click="downloadWorkspace('json')" />
        <Button icon="pi pi-file-export" :label="t('workspace.exportMarkdown')" severity="secondary" @click="downloadWorkspace('markdown')" />
      </template>
    </PageHeader>

    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <Message v-if="notice" severity="success" :closable="false">{{ notice }}</Message>

    <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(320px,1fr))] uno-gap-4">
      <Card>
        <template #title>{{ t('workspace.importExport') }}</template>
        <template #content>
          <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
            <Select v-model="workspaceImport.mode" :options="importModes" option-label="label" option-value="value" :disabled="!canWrite" />
            <Button icon="pi pi-upload" :label="t('workspace.importWorkspace')" :disabled="!canWrite" @click="importWorkspaceSnapshot" />
          </div>
          <Textarea
            v-model="workspaceImport.content"
            rows="8"
            auto-resize
            :placeholder="t('workspace.importPlaceholder')"
            class="uno-mt-3 uno-w-full"
            :disabled="!canWrite"
          />
        </template>
      </Card>

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
            <InputText v-model="note.ticker" :placeholder="t('workspace.tickerOptional')" :disabled="!canWrite" />
            <InputText v-model="note.tags" :placeholder="t('workspace.tagsPlaceholder')" :disabled="!canWrite" />
          </div>
          <Textarea v-model="note.content" rows="4" auto-resize :placeholder="t('workspace.notePlaceholder')" class="uno-mt-3 uno-w-full" :disabled="!canWrite" />
          <Button icon="pi pi-save" :label="t('workspace.saveNote')" class="uno-mt-3" :disabled="!canWrite" @click="saveNote" />
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
            <InputText v-model="member.name" :placeholder="t('workspace.name')" :disabled="!canWrite" />
            <Select v-model="member.role" :options="memberRoles" option-label="label" option-value="value" :placeholder="t('workspace.role')" :disabled="!canWrite" />
            <Button icon="pi pi-user-plus" :label="t('common.add')" :disabled="!canWrite" @click="saveMember" />
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
        <template #title>{{ t('workspace.memberWorkspace') }}</template>
        <template #content>
          <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
            <Select
              v-model="selectedMemberId"
              :options="memberWorkspaceOptions"
              option-label="label"
              option-value="value"
              :placeholder="t('workspace.memberWorkspace')"
              @change="loadMemberWorkspace"
            />
          </div>
          <div v-if="memberWorkspace" class="uno-mt-3 uno-grid uno-gap-[0.65rem]">
            <div class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ memberWorkspace.member.name }}</span>
                <Tag :value="memberWorkspace.member.role || t('workspace.member')" severity="secondary" />
              </div>
              <small class="uno-text-[#6f8183]">
                {{ t('workspace.assignedActions') }}: {{ memberWorkspace.summary.assigned_action_count }} ·
                {{ t('workspace.pendingReviews') }}: {{ memberWorkspace.summary.pending_review_count }} ·
                {{ t('workspace.mentions') }}: {{ memberWorkspace.summary.mention_count }}
              </small>
            </div>
            <div class="uno-grid uno-gap-[0.65rem]">
              <div v-for="item in memberWorkspace.assigned_actions" :key="item.run_id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
                <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                  <span>{{ item.ticker || item.run_id }}</span>
                  <Tag :value="item.action_status || t('common.pending')" severity="info" />
                </div>
                <small class="uno-text-[#6f8183]">{{ item.next_action || item.note || t('workspace.noMemberWorkspace') }}</small>
              </div>
              <div v-for="item in memberWorkspace.pending_reviews" :key="item.run_id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
                <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                  <span>{{ item.run_id }}</span>
                  <Tag :value="item.status" severity="warn" />
                </div>
                <small class="uno-text-[#6f8183]">{{ item.note || t('workspace.noMemberWorkspace') }}</small>
              </div>
              <div v-for="item in memberWorkspace.recent_comments" :key="item.id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
                <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                  <span>{{ item.author }}</span>
                  <small class="uno-text-[#6f8183]">{{ formatDateTime(item.created_at) }}</small>
                </div>
                <small class="uno-text-[#6f8183]">{{ item.content }}</small>
              </div>
            </div>
          </div>
          <p v-else class="uno-mt-3 uno-text-[#6f8183]">{{ t('workspace.noMemberWorkspace') }}</p>
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
        <template #title>{{ t('workspace.calendar') }}</template>
        <template #content>
          <div class="uno-grid uno-gap-[0.65rem]">
            <div v-for="day in asArray(calendar?.days).slice(0, 7)" :key="day.date" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ day.date }}</span>
                <Tag :value="String(asArray(day.events).length)" severity="info" />
              </div>
              <small class="uno-text-[#6f8183]">{{ asArray(day.events).map((event) => event.title).join(' · ') || t('workspace.noCalendarEvents') }}</small>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('workspace.actionBoard') }}</template>
        <template #content>
          <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(220px,1fr))] uno-gap-4">
            <div v-for="column in actionBoardColumns" :key="column.key" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ column.label }}</span>
                <Tag :value="String(column.items.length)" severity="info" />
              </div>
              <div class="uno-mt-3 uno-grid uno-gap-[0.65rem]">
                <div v-for="item in column.items" :key="item.run_id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-[#fbfdfd] uno-p-3">
                  <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                    <span>{{ item.ticker || item.run_id }}</span>
                    <Tag :value="item.priority || t('common.na')" severity="secondary" />
                  </div>
                  <small class="uno-text-[#6f8183]">{{ item.next_action || item.note || t('workspace.noActionBoard') }}</small>
                  <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                    <Select
                      :model-value="item.action_status"
                      :options="actionStatusOptions"
                      option-label="label"
                      option-value="value"
                      :disabled="!canWrite"
                      @change="updatePinnedRunStatus(item.run_id, $event.value)"
                    />
                    <Select
                      :model-value="item.assignee || ''"
                      :options="memberSelectOptions"
                      option-label="label"
                      option-value="value"
                      :placeholder="t('common.optional')"
                      :disabled="!canWrite"
                      @change="updatePinnedRunAssignee(item.run_id, $event.value)"
                    />
                  </div>
                </div>
                <p v-if="!column.items.length" class="uno-text-[#6f8183]">{{ t('workspace.noActionBoard') }}</p>
              </div>
            </div>
          </div>
        </template>
      </Card>

      <Card>
        <template #title>{{ t('workspace.savedViewsAndShares') }}</template>
        <template #content>
          <div class="uno-mb-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
            <InputText v-model="savedViewForm.name" :placeholder="t('workspace.saveCurrentView')" :disabled="!canWrite" />
            <InputText v-model="savedViewForm.group" :placeholder="t('workspace.viewGroup')" :disabled="!canWrite" />
            <Button icon="pi pi-save" :label="t('workspace.saveCurrentView')" severity="secondary" :disabled="!canWrite" @click="saveCurrentView" />
            <Button icon="pi pi-download" :label="t('workspace.exportPublicShares')" severity="secondary" @click="exportPublicShares" />
          </div>
          <div class="uno-grid uno-gap-[0.65rem]">
            <div v-for="view in views" :key="view.id" class="uno-rounded-lg uno-border uno-border-[#dde7e7] uno-bg-white uno-p-3">
              <div class="uno-flex uno-items-center uno-justify-between uno-gap-3 uno-font-700">
                <span>{{ view.name }}</span>
                <Tag :value="view.group || t('workspace.view')" severity="info" />
              </div>
              <small class="uno-text-[#6f8183]">{{ view.url }}</small>
              <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
                <Button icon="pi pi-copy" :label="t('workspace.duplicateView')" severity="secondary" :disabled="!canWrite" @click="duplicateView(view.id)" />
                  <Button
                    :icon="view.archived ? 'pi pi-inbox' : 'pi pi-folder'"
                    :label="view.archived ? t('workspace.restoreView') : t('workspace.archiveView')"
                    severity="secondary"
                    :disabled="!canWrite"
                    @click="toggleViewArchive(view)"
                  />
                <Button icon="pi pi-trash" :label="t('common.delete')" severity="danger" outlined :disabled="!canWrite" @click="deleteView(view.id)" />
              </div>
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
import { useRoute } from 'vue-router';

import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPatch, apiPost, buildApiUrl } from '../services/api';
import { useSession } from '../stores/session';
import { asArray, formatDateTime, type JsonRecord } from '../utils/format';

const session = useSession();
const route = useRoute();
const canWrite = computed(() => session.canWrite.value);
const searchQuery = ref('');
const searchResults = ref<JsonRecord | null>(null);
const notes = ref<JsonRecord[]>([]);
const members = ref<JsonRecord[]>([]);
const memberWorkspace = ref<JsonRecord | null>(null);
const reviews = ref<JsonRecord | null>(null);
const timeline = ref<JsonRecord | null>(null);
const calendar = ref<JsonRecord | null>(null);
const actionBoard = ref<JsonRecord | null>(null);
const views = ref<JsonRecord[]>([]);
const shares = ref<JsonRecord[]>([]);
const error = ref('');
const notice = ref('');
const note = reactive({ ticker: '', tags: '', content: '' });
const member = reactive({ name: '', role: '' });
const workspaceImport = reactive({ content: '', mode: 'replace' });
const savedViewForm = reactive({ name: '', group: '' });
const selectedMemberId = ref(session.state.currentMemberId);
const { t } = useI18n();
const memberRoles = computed(() => [
  { label: t('workspace.roleAnalyst'), value: 'analyst' },
  { label: t('workspace.roleReviewer'), value: 'reviewer' },
  { label: t('workspace.roleOperator'), value: 'operator' },
  { label: t('workspace.roleLead'), value: 'lead' },
  { label: t('workspace.roleObserver'), value: 'observer' },
]);
const memberWorkspaceOptions = computed(() => members.value.map((item) => ({
  label: String(item.name || item.id || ''),
  value: String(item.id || ''),
})));
const memberSelectOptions = computed(() => [
  { label: t('common.optional'), value: '' },
  ...members.value.map((item) => ({
    label: String(item.name || item.id || ''),
    value: String(item.name || ''),
  })),
]);
const importModes = computed(() => [
  { label: t('workspace.importReplace'), value: 'replace' },
  { label: t('workspace.importMerge'), value: 'merge' },
]);
const actionStatusOptions = computed(() => [
  { label: t('runs.actionTodo'), value: 'todo' },
  { label: t('runs.actionDoing'), value: 'doing' },
  { label: t('runs.actionDone'), value: 'done' },
]);
const actionBoardColumns = computed(() => [
  { key: 'todo', label: t('runs.actionTodo'), items: asArray(actionBoard.value?.todo) },
  { key: 'doing', label: t('runs.actionDoing'), items: asArray(actionBoard.value?.doing) },
  { key: 'done', label: t('runs.actionDone'), items: asArray(actionBoard.value?.done) },
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
    const [noteItems, memberItems, reviewPayload, timelinePayload, calendarPayload, actionBoardPayload, viewItems, shareItems] = await Promise.all([
      apiGet<JsonRecord[]>('/api/notes', context),
      apiGet<JsonRecord[]>('/api/members', context),
      apiGet<JsonRecord>('/api/reviews', context),
      apiGet<JsonRecord>('/api/timeline', context),
      apiGet<JsonRecord>('/api/calendar', context),
      apiGet<JsonRecord>('/api/action-board', context),
      apiGet<JsonRecord[]>('/api/views', context),
      apiGet<JsonRecord[]>('/api/public-shares', context),
    ]);
    notes.value = noteItems;
    members.value = memberItems;
    if (selectedMemberId.value && !members.value.some((item) => String(item.id) === selectedMemberId.value)) {
      selectedMemberId.value = '';
      session.setCurrentMemberId('');
    }
    reviews.value = reviewPayload;
    timeline.value = timelinePayload;
    calendar.value = calendarPayload;
    actionBoard.value = actionBoardPayload;
    views.value = viewItems;
    shares.value = shareItems;
    await loadMemberWorkspace();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('workspace.loadError');
  }
}

function downloadWorkspace(format: 'json' | 'markdown') {
  const path = format === 'json' ? '/api/workspace/export?format=json' : '/api/workspace/export?format=markdown';
  window.open(buildApiUrl(path, session.apiContext.value), '_blank', 'noopener');
}

function exportPublicShares() {
  window.open(buildApiUrl('/api/public-shares/export', session.apiContext.value), '_blank', 'noopener');
}

async function importWorkspaceSnapshot() {
  if (!workspaceImport.content.trim()) return;
  try {
    const result = await apiPost<JsonRecord>(
      '/api/workspace/import',
      {
        content: workspaceImport.content,
        mode: workspaceImport.mode,
      },
      session.apiContext.value,
    );
    workspaceImport.content = '';
    notice.value = `${t('workspace.importWorkspace')}: ${result.mode}`;
    await loadAll();
  } catch (exc) {
    error.value = exc instanceof Error ? exc.message : t('workspace.loadError');
  }
}

async function loadMemberWorkspace() {
  if (!selectedMemberId.value) {
    memberWorkspace.value = null;
    return;
  }
  const selectedMember = members.value.find((item) => String(item.id) === selectedMemberId.value);
  if (selectedMember) {
    session.setCurrentMemberId(String(selectedMember.id));
  }
  memberWorkspace.value = await apiGet<JsonRecord>(
    `/api/members/${encodeURIComponent(String(selectedMember?.id || selectedMemberId.value))}/workspace`,
    session.apiContext.value,
  );
}

async function saveCurrentView() {
  if (!savedViewForm.name.trim()) return;
  await apiPost<JsonRecord>(
    '/api/views',
    {
      name: savedViewForm.name.trim(),
      url: route.fullPath,
      visible_panels: ['import-export', 'search', 'notes', 'members', 'member-workspace', 'reviews', 'timeline', 'calendar', 'action-board', 'saved-views'],
      group: savedViewForm.group.trim() || null,
      member_id: session.state.currentMemberId || null,
    },
    session.apiContext.value,
  );
  savedViewForm.name = '';
  savedViewForm.group = '';
  views.value = await apiGet<JsonRecord[]>('/api/views', session.apiContext.value);
}

async function duplicateView(viewId: string) {
  await apiPost<JsonRecord>(`/api/views/${encodeURIComponent(viewId)}/duplicate`, {}, session.apiContext.value);
  views.value = await apiGet<JsonRecord[]>('/api/views', session.apiContext.value);
}

async function toggleViewArchive(view: JsonRecord) {
  await apiPost<JsonRecord>(
    '/api/views/bulk',
    {
      ids: [view.id],
      action: view.archived ? 'restore' : 'archive',
    },
    session.apiContext.value,
  );
  views.value = await apiGet<JsonRecord[]>('/api/views', session.apiContext.value);
}

async function deleteView(viewId: string) {
  await apiDelete(`/api/views/${encodeURIComponent(viewId)}`, session.apiContext.value);
  views.value = await apiGet<JsonRecord[]>('/api/views', session.apiContext.value);
}

async function updatePinnedRunStatus(runId: string, action_status: string) {
  await apiPatch<JsonRecord>(
    `/api/pinned-runs/${encodeURIComponent(runId)}/status`,
    { action_status },
    session.apiContext.value,
  );
  actionBoard.value = await apiGet<JsonRecord>('/api/action-board', session.apiContext.value);
}

async function updatePinnedRunAssignee(runId: string, assignee: string) {
  await apiPatch<JsonRecord>(
    `/api/pinned-runs/${encodeURIComponent(runId)}/assignee`,
    { assignee: assignee || null },
    session.apiContext.value,
  );
  actionBoard.value = await apiGet<JsonRecord>('/api/action-board', session.apiContext.value);
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
