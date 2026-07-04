<template>
  <section class="uno-grid uno-gap-4">
    <PageHeader
      :eyebrow="t('tenants.detailEyebrow')"
      :title="headerTitle"
      :description="t('tenants.detailDescription', { tenantId: routeTenantId || t('common.na') })"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" :loading="loading" @click="refreshPage" />
      </template>
    </PageHeader>

    <Message v-if="pageError" severity="error" :closable="false">{{ pageError }}</Message>
    <Message v-if="notice" severity="success" :closable="false">{{ notice }}</Message>

    <Card v-if="tenant">
      <template #title>{{ t('tenants.detailSummary') }}</template>
      <template #content>
        <div class="uno-grid uno-gap-4 md:uno-grid-cols-[minmax(0,1fr)_auto]">
          <dl class="uno-grid uno-gap-3 sm:uno-grid-cols-2">
            <div>
              <dt class="uno-text-sm uno-text-[#6f8183]">{{ t('tenants.tenantId') }}</dt>
              <dd class="uno-mt-1 uno-font-semibold uno-text-[#132a2d]">{{ tenant.tenant_id }}</dd>
            </div>
            <div>
              <dt class="uno-text-sm uno-text-[#6f8183]">{{ t('tenants.displayName') }}</dt>
              <dd class="uno-mt-1">{{ tenant.display_name }}</dd>
            </div>
            <div>
              <dt class="uno-text-sm uno-text-[#6f8183]">{{ t('common.status') }}</dt>
              <dd class="uno-mt-1">{{ tenantStatusLabel(tenant) }}</dd>
            </div>
            <div>
              <dt class="uno-text-sm uno-text-[#6f8183]">{{ t('tenants.userCount') }}</dt>
              <dd class="uno-mt-1">{{ tenant.user_count }}</dd>
            </div>
            <div>
              <dt class="uno-text-sm uno-text-[#6f8183]">{{ t('tenants.activeAdminCount') }}</dt>
              <dd class="uno-mt-1">{{ tenant.active_admin_count }}</dd>
            </div>
            <div>
              <dt class="uno-text-sm uno-text-[#6f8183]">{{ t('common.created') }}</dt>
              <dd class="uno-mt-1">{{ formatDateTime(tenant.created_at) }}</dd>
            </div>
            <div>
              <dt class="uno-text-sm uno-text-[#6f8183]">{{ t('tenants.lastUpdated') }}</dt>
              <dd class="uno-mt-1">{{ formatDateTime(tenant.updated_at) }}</dd>
            </div>
          </dl>

          <div class="uno-grid uno-content-start uno-gap-2">
            <Button
              v-if="!tenant.archived"
              data-testid="toggle-tenant-disabled"
              icon="pi pi-ban"
              :label="tenant.disabled ? t('tenants.enableTenant') : t('tenants.disableTenant')"
              severity="secondary"
              :loading="saving"
              @click="toggleTenantDisabled"
            />
            <Button
              data-testid="archive-tenant"
              :icon="tenant.archived ? 'pi pi-history' : 'pi pi-box'"
              :label="tenant.archived ? t('tenants.unarchiveTenant') : t('tenants.archiveTenant')"
              :severity="tenant.archived ? 'secondary' : 'danger'"
              outlined
              :loading="archiving"
              @click="toggleTenantArchived"
            />
          </div>
        </div>
      </template>
    </Card>

    <AdminUserDirectory
      v-if="tenant"
      ref="directory"
      :list-path="tenantUsersPath"
      :create-path="tenantUsersPath"
      :update-path="tenantUserPath"
      :delete-path="tenantUserPath"
      :read-only="tenant.archived"
    />
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import Message from 'primevue/message';
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';

import AdminUserDirectory from '../components/AdminUserDirectory.vue';
import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiGet, apiPatch } from '../services/api';
import { formatDateTime } from '../utils/format';

type AdminTenantResponse = {
  id: string;
  tenant_id: string;
  display_name: string;
  disabled: boolean;
  archived: boolean;
  user_count: number;
  active_admin_count: number;
  created_at: number;
  updated_at: number;
};

const route = useRoute();
const { t } = useI18n();
const directory = ref<{ loadUsers: () => Promise<void> } | null>(null);
const loading = ref(false);
const saving = ref(false);
const archiving = ref(false);
const tenant = ref<AdminTenantResponse | null>(null);
const pageError = ref('');
const notice = ref('');

const routeTenantId = computed(() => {
  const value = route.params.tenantId;
  return Array.isArray(value) ? String(value[0] || '') : String(value || '');
});
const tenantDetailPath = computed(() => `/api/admin/tenants/${encodeURIComponent(routeTenantId.value)}`);
const tenantUsersPath = computed(() => `${tenantDetailPath.value}/users`);
const headerTitle = computed(() => (
  tenant.value ? `${tenant.value.display_name} (${tenant.value.tenant_id})` : routeTenantId.value
));

function tenantUserPath(userId: string) {
  return `${tenantUsersPath.value}/${encodeURIComponent(userId)}`;
}

function tenantStatusLabel(currentTenant: AdminTenantResponse): string {
  if (currentTenant.archived) {
    return t('common.archived');
  }
  if (currentTenant.disabled) {
    return t('users.disabled');
  }
  return t('common.active');
}

async function loadTenant() {
  loading.value = true;
  pageError.value = '';
  try {
    const payload = await apiGet<{ tenant: AdminTenantResponse }>(tenantDetailPath.value);
    tenant.value = payload.tenant;
  } catch (exc) {
    pageError.value = exc instanceof Error ? exc.message : t('tenants.loadDetailError');
  } finally {
    loading.value = false;
  }
}

async function refreshDirectory() {
  await nextTick();
  await directory.value?.loadUsers();
}

async function refreshPage() {
  await loadTenant();
  await refreshDirectory();
}

async function toggleTenantDisabled() {
  if (!tenant.value) {
    return;
  }
  saving.value = true;
  pageError.value = '';
  notice.value = '';
  try {
    const disabled = !tenant.value.disabled;
    const payload = await apiPatch<{ tenant: AdminTenantResponse }>(tenantDetailPath.value, { disabled });
    notice.value = disabled
      ? t('tenants.tenantDisabled', { tenantId: payload.tenant.tenant_id })
      : t('tenants.tenantEnabled', { tenantId: payload.tenant.tenant_id });
    tenant.value = payload.tenant;
  } catch (exc) {
    pageError.value = exc instanceof Error ? exc.message : t('tenants.updateError');
  } finally {
    saving.value = false;
  }
}

async function toggleTenantArchived() {
  if (!tenant.value) {
    return;
  }
  archiving.value = true;
  pageError.value = '';
  notice.value = '';
  try {
    const archived = !tenant.value.archived;
    const payload = await apiPatch<{ tenant: AdminTenantResponse }>(tenantDetailPath.value, { archived });
    notice.value = archived
      ? t('tenants.tenantArchived', { tenantId: payload.tenant.tenant_id })
      : t('tenants.tenantUnarchived', { tenantId: payload.tenant.tenant_id });
    tenant.value = payload.tenant;
  } catch (exc) {
    pageError.value = exc instanceof Error ? exc.message : t('tenants.updateError');
  } finally {
    archiving.value = false;
  }
}

watch(routeTenantId, async (tenantId, previousTenantId) => {
  if (!tenantId || tenantId === previousTenantId) {
    return;
  }
  tenant.value = null;
  await refreshPage();
});

onMounted(loadTenant);
</script>
