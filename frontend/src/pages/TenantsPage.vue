<template>
  <section class="uno-grid uno-gap-4">
    <PageHeader
      :eyebrow="t('tenants.eyebrow')"
      :title="t('tenants.title')"
      :description="t('tenants.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" :loading="loading" @click="loadTenants" />
      </template>
    </PageHeader>

    <Message v-if="pageError" severity="error" :closable="false">{{ pageError }}</Message>
    <Message v-if="notice" severity="success" :closable="false">{{ notice }}</Message>

    <Card>
      <template #title>{{ t('tenants.filters') }}</template>
      <template #content>
        <div class="uno-grid uno-gap-3 md:uno-grid-cols-[repeat(4,minmax(0,1fr))_auto]">
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('tenants.filterName') }}</span>
            <InputText v-model="filters.name" data-testid="tenant-filter-name" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('common.status') }}</span>
            <select
              v-model="filters.status"
              data-testid="tenant-filter-status"
              class="uno-rounded-md uno-border uno-border-[#dce7e7] uno-bg-white uno-px-3 uno-py-2"
            >
              <option value="">{{ t('common.all') }}</option>
              <option value="active">{{ t('common.active') }}</option>
              <option value="disabled">{{ t('users.disabled') }}</option>
              <option value="expired">{{ t('tenants.expired') }}</option>
            </select>
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('tenants.createdFrom') }}</span>
            <DateTimeInput
              v-model="filters.createdFrom"
              data-testid="tenant-filter-created-from"
            />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('tenants.createdTo') }}</span>
            <DateTimeInput
              v-model="filters.createdTo"
              data-testid="tenant-filter-created-to"
            />
          </label>
          <div class="uno-flex uno-flex-wrap uno-items-end uno-gap-2">
            <Button data-testid="tenant-filter-submit" icon="pi pi-search" :label="t('common.search')" @click="loadTenants" />
            <Button icon="pi pi-undo" :label="t('tenants.resetFilters')" severity="secondary" @click="resetFilters" />
          </div>
        </div>
      </template>
    </Card>

    <div class="uno-flex uno-flex-wrap uno-items-center uno-justify-between uno-gap-3">
      <Button data-testid="open-create-tenant" icon="pi pi-plus" :label="t('tenants.createAction')" @click="openCreateDialog" />
      <Button
        data-testid="batch-disable-tenants"
        icon="pi pi-ban"
        :label="t('tenants.batchDisable')"
        severity="secondary"
        :disabled="selectedTenantIds.length === 0"
        :loading="batchDisabling"
        @click="disableSelectedTenants"
      />
    </div>

    <Card>
      <template #title>{{ t('tenants.directory') }}</template>
      <template #content>
        <div class="uno-overflow-x-auto">
          <table class="uno-min-w-full uno-border-collapse uno-text-sm">
            <thead>
              <tr class="uno-border-b uno-border-[#dce7e7] uno-text-left uno-text-[#6f8183]">
                <th class="uno-w-10 uno-px-3 uno-py-2">
                  <input
                    type="checkbox"
                    :checked="allSelectableTenantsSelected"
                    :disabled="selectableTenants.length === 0"
                    @change="toggleSelectAll(($event.target as HTMLInputElement).checked)"
                  >
                </th>
                <th class="uno-px-3 uno-py-2">{{ t('tenants.tenantId') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('tenants.displayName') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('common.status') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('tenants.userCount') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('tenants.activeAdminCount') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('common.created') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('users.expiresAt') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('tenants.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tenant in tenants" :key="tenant.id" class="uno-border-b uno-border-[#eef4f4]">
                <td class="uno-px-3 uno-py-3 uno-align-top">
                  <input
                    :data-testid="`tenant-select-${tenant.tenant_id}`"
                    type="checkbox"
                    :checked="selectedTenantIds.includes(tenant.tenant_id)"
                    :disabled="!canSelectTenant(tenant)"
                    @change="toggleTenantSelection(tenant.tenant_id, ($event.target as HTMLInputElement).checked)"
                  >
                </td>
                <td class="uno-px-3 uno-py-3 uno-align-top">
                  <button
                    type="button"
                    class="uno-font-semibold uno-text-[#132a2d] uno-underline-offset-2 hover:uno-underline"
                    @click="openTenant(tenant.tenant_id)"
                  >
                    {{ tenant.tenant_id }}
                  </button>
                </td>
                <td class="uno-px-3 uno-py-3 uno-align-top">{{ tenant.display_name }}</td>
                <td class="uno-px-3 uno-py-3 uno-align-top">{{ tenantStatusLabel(tenant) }}</td>
                <td class="uno-px-3 uno-py-3 uno-align-top">{{ tenant.user_count }}</td>
                <td class="uno-px-3 uno-py-3 uno-align-top">{{ tenant.active_admin_count }}</td>
                <td class="uno-px-3 uno-py-3 uno-align-top">{{ formatDateTime(tenant.created_at) }}</td>
                <td class="uno-px-3 uno-py-3 uno-align-top">{{ formatDateTime(tenant.expires_at) }}</td>
                <td class="uno-px-3 uno-py-3 uno-align-top">
                  <div class="uno-flex uno-flex-wrap uno-gap-2">
                    <Button
                      :data-testid="`edit-tenant-${tenant.tenant_id}`"
                      icon="pi pi-pencil"
                      :label="t('common.edit')"
                      severity="secondary"
                      @click="openEditDialog(tenant)"
                    />
                    <Button
                      :data-testid="`toggle-tenant-${tenant.tenant_id}`"
                      icon="pi pi-ban"
                      :label="tenant.disabled ? t('tenants.enableTenant') : t('tenants.disableTenant')"
                      severity="secondary"
                      :loading="tenant.saving"
                      @click="toggleTenantDisabled(tenant)"
                    />
                  </div>
                  <Message v-if="tenant.error" severity="error" :closable="false" class="uno-mt-2">{{ tenant.error }}</Message>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </Card>

    <Dialog v-model:visible="dialogOpen" modal :header="dialogTitle" :style="{ width: '32rem' }">
      <div class="uno-grid uno-gap-3">
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('tenants.displayName') }}</span>
          <InputText v-model="tenantForm.display_name" data-testid="tenant-form-display-name" />
        </label>
        <label class="uno-grid uno-gap-[0.35rem]">
          <span class="uno-text-[#6f8183]">{{ t('users.expiresAt') }}</span>
          <DateTimeInput v-model="tenantForm.expires_at" data-testid="tenant-form-expires-at" mode="datetime" />
        </label>
        <Message v-if="dialogError" severity="error" :closable="false">{{ dialogError }}</Message>
        <div class="uno-flex uno-justify-end uno-gap-2">
          <Button :label="t('common.cancel')" severity="secondary" @click="closeDialog" />
          <Button
            data-testid="tenant-dialog-submit"
            :label="dialogMode === 'create' ? t('tenants.createAction') : t('common.save')"
            :loading="dialogSaving"
            @click="submitTenantForm"
          />
        </div>
      </div>
    </Dialog>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import { computed, onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import DateTimeInput from '../components/DateTimeInput.vue';
import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiGet, apiPatch, apiPost } from '../services/api';
import { formatDateTime, formatDateTimeInputValue } from '../utils/format';

type TenantStatus = 'active' | 'disabled' | 'expired';

type AdminTenantResponse = {
  id: string;
  tenant_id: string;
  display_name: string;
  disabled: boolean;
  expires_at: number | null;
  status: TenantStatus;
  user_count: number;
  active_admin_count: number;
  created_at: number;
  updated_at: number;
};

type ManagedTenant = AdminTenantResponse & {
  saving: boolean;
  error: string;
};

const router = useRouter();
const { t } = useI18n();
const loading = ref(false);
const batchDisabling = ref(false);
const pageError = ref('');
const notice = ref('');
const tenants = ref<ManagedTenant[]>([]);
const selectedTenantIds = ref<string[]>([]);
const dialogOpen = ref(false);
const dialogMode = ref<'create' | 'edit'>('create');
const dialogSaving = ref(false);
const dialogError = ref('');
const editingTenantId = ref('');

const filters = reactive({
  name: '',
  status: '',
  createdFrom: '',
  createdTo: '',
});

const tenantForm = reactive({
  display_name: '',
  expires_at: '',
});

const dialogTitle = computed(() => (
  dialogMode.value === 'create' ? t('tenants.createTenant') : t('tenants.editTenant')
));

const selectableTenants = computed(() => tenants.value.filter((tenant) => canSelectTenant(tenant)));
const allSelectableTenantsSelected = computed(() => (
  selectableTenants.value.length > 0
  && selectableTenants.value.every((tenant) => selectedTenantIds.value.includes(tenant.tenant_id))
));

function decorateTenant(tenant: AdminTenantResponse): ManagedTenant {
  return {
    ...tenant,
    saving: false,
    error: '',
  };
}

function canSelectTenant(tenant: AdminTenantResponse): boolean {
  return tenant.status === 'active';
}

function tenantStatusLabel(tenant: AdminTenantResponse): string {
  if (tenant.status === 'disabled') {
    return t('users.disabled');
  }
  if (tenant.status === 'expired') {
    return t('tenants.expired');
  }
  return t('common.active');
}

function toApiDateTime(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const date = new Date(trimmed);
  return Number.isNaN(date.getTime()) ? null : date.getTime();
}

function buildListPath(): string {
  const params = new URLSearchParams();
  if (filters.name.trim()) {
    params.set('name', filters.name.trim());
  }
  if (filters.status.trim()) {
    params.set('status', filters.status.trim());
  }
  if (filters.createdFrom.trim()) {
    params.set('created_from', String(new Date(`${filters.createdFrom.trim()}T00:00`).getTime()));
  }
  if (filters.createdTo.trim()) {
    params.set('created_to', String(new Date(`${filters.createdTo.trim()}T23:59:59.999`).getTime()));
  }
  const query = params.toString();
  return query ? `/api/admin/tenants?${query}` : '/api/admin/tenants';
}

function resetSelections() {
  selectedTenantIds.value = selectedTenantIds.value.filter((tenantId) => (
    tenants.value.some((tenant) => tenant.tenant_id === tenantId && canSelectTenant(tenant))
  ));
}

async function loadTenants() {
  loading.value = true;
  pageError.value = '';
  try {
    const payload = await apiGet<{ tenants: AdminTenantResponse[] }>(buildListPath());
    tenants.value = payload.tenants.map(decorateTenant);
    resetSelections();
  } catch (exc) {
    pageError.value = exc instanceof Error ? exc.message : t('tenants.loadError');
  } finally {
    loading.value = false;
  }
}

function resetFilters() {
  filters.name = '';
  filters.status = '';
  filters.createdFrom = '';
  filters.createdTo = '';
  void loadTenants();
}

function openTenant(tenantId: string) {
  void router.push({ name: 'tenant-detail', params: { tenantId } });
}

function toggleTenantSelection(tenantId: string, checked: boolean) {
  if (checked) {
    if (!selectedTenantIds.value.includes(tenantId)) {
      selectedTenantIds.value = [...selectedTenantIds.value, tenantId];
    }
    return;
  }
  selectedTenantIds.value = selectedTenantIds.value.filter((value) => value !== tenantId);
}

function toggleSelectAll(checked: boolean) {
  selectedTenantIds.value = checked ? selectableTenants.value.map((tenant) => tenant.tenant_id) : [];
}

function resetTenantForm() {
  tenantForm.display_name = '';
  tenantForm.expires_at = '';
  editingTenantId.value = '';
  dialogError.value = '';
}

function openCreateDialog() {
  dialogMode.value = 'create';
  resetTenantForm();
  dialogOpen.value = true;
}

function openEditDialog(tenant: AdminTenantResponse) {
  dialogMode.value = 'edit';
  editingTenantId.value = tenant.tenant_id;
  tenantForm.display_name = tenant.display_name;
  tenantForm.expires_at = formatDateTimeInputValue(tenant.expires_at);
  dialogError.value = '';
  dialogOpen.value = true;
}

function closeDialog() {
  dialogOpen.value = false;
  resetTenantForm();
}

async function submitTenantForm() {
  dialogSaving.value = true;
  dialogError.value = '';
  notice.value = '';
  const payload = {
    display_name: tenantForm.display_name.trim(),
    expires_at: toApiDateTime(tenantForm.expires_at),
  };
  try {
    if (dialogMode.value === 'create') {
      const created = await apiPost<{ tenant: AdminTenantResponse }>('/api/admin/tenants', payload);
      notice.value = t('tenants.tenantCreated', { tenantId: created.tenant.tenant_id });
      closeDialog();
      await loadTenants();
      openTenant(created.tenant.tenant_id);
      return;
    }

    await apiPatch<{ tenant: AdminTenantResponse }>(
      `/api/admin/tenants/${encodeURIComponent(editingTenantId.value)}`,
      payload,
    );
    notice.value = t('tenants.tenantUpdated', { tenantId: editingTenantId.value });
    closeDialog();
    await loadTenants();
  } catch (exc) {
    dialogError.value = exc instanceof Error ? exc.message : t('tenants.updateError');
  } finally {
    dialogSaving.value = false;
  }
}

async function toggleTenantDisabled(tenant: ManagedTenant) {
  tenant.saving = true;
  tenant.error = '';
  notice.value = '';
  try {
    const payload = await apiPatch<{ tenant: AdminTenantResponse }>(
      `/api/admin/tenants/${encodeURIComponent(tenant.tenant_id)}`,
      { disabled: !tenant.disabled },
    );
    notice.value = payload.tenant.disabled
      ? t('tenants.tenantDisabled', { tenantId: payload.tenant.tenant_id })
      : t('tenants.tenantEnabled', { tenantId: payload.tenant.tenant_id });
    await loadTenants();
  } catch (exc) {
    tenant.error = exc instanceof Error ? exc.message : t('tenants.updateError');
  } finally {
    tenant.saving = false;
  }
}

async function disableSelectedTenants() {
  batchDisabling.value = true;
  pageError.value = '';
  notice.value = '';
  try {
    const payload = await apiPost<{ updated_count: number; skipped_count: number }>(
      '/api/admin/tenants/batch-disable',
      { tenant_ids: selectedTenantIds.value },
    );
    notice.value = t('tenants.batchDisabled', { count: payload.updated_count });
    selectedTenantIds.value = [];
    await loadTenants();
  } catch (exc) {
    pageError.value = exc instanceof Error ? exc.message : t('tenants.updateError');
  } finally {
    batchDisabling.value = false;
  }
}

onMounted(loadTenants);
</script>
