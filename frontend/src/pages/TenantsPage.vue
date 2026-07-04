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
      <template #title>{{ t('tenants.createTenant') }}</template>
      <template #content>
        <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(180px,1fr))] uno-gap-3">
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('tenants.tenantId') }}</span>
            <InputText v-model="createForm.tenant_id" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('tenants.displayName') }}</span>
            <InputText v-model="createForm.display_name" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('tenants.adminUsername') }}</span>
            <InputText v-model="createForm.admin.username" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('tenants.adminEmail') }}</span>
            <InputText v-model="createForm.admin.email" type="email" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('tenants.adminDisplayName') }}</span>
            <InputText v-model="createForm.admin.display_name" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('tenants.adminPassword') }}</span>
            <InputText v-model="createForm.admin.password" type="password" />
          </label>
        </div>
        <Message v-if="createError" severity="error" :closable="false" class="uno-mt-3">{{ createError }}</Message>
        <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
          <Button
            data-testid="create-tenant-submit"
            icon="pi pi-plus"
            :label="t('tenants.createAction')"
            :loading="creating"
            @click="createTenant"
          />
        </div>
      </template>
    </Card>

    <Card>
      <template #title>{{ t('tenants.directory') }}</template>
      <template #content>
        <div class="uno-overflow-x-auto">
          <table class="uno-min-w-full uno-border-collapse uno-text-sm">
            <thead>
              <tr class="uno-border-b uno-border-[#dce7e7] uno-text-left uno-text-[#6f8183]">
                <th class="uno-px-3 uno-py-2">{{ t('tenants.tenantId') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('tenants.displayName') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('common.status') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('tenants.userCount') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('tenants.activeAdminCount') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('common.created') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('tenants.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="tenant in tenants" :key="tenant.id" class="uno-border-b uno-border-[#eef4f4]">
                <td class="uno-px-3 uno-py-3 uno-align-top">
                  <strong class="uno-break-words uno-text-[#132a2d]">{{ tenant.tenant_id }}</strong>
                </td>
                <td class="uno-px-3 uno-py-3 uno-align-top">{{ tenant.display_name }}</td>
                <td class="uno-px-3 uno-py-3 uno-align-top">{{ tenantStatusLabel(tenant) }}</td>
                <td class="uno-px-3 uno-py-3 uno-align-top">{{ tenant.user_count }}</td>
                <td class="uno-px-3 uno-py-3 uno-align-top">{{ tenant.active_admin_count }}</td>
                <td class="uno-px-3 uno-py-3 uno-align-top">{{ tenant.created_at }}</td>
                <td class="uno-px-3 uno-py-3 uno-align-top">
                  <div class="uno-grid uno-gap-2">
                    <Button
                      :data-testid="`open-tenant-${tenant.tenant_id}`"
                      icon="pi pi-external-link"
                      :label="t('tenants.openTenant')"
                      severity="secondary"
                      @click="openTenant(tenant)"
                    />
                    <Button
                      :data-testid="`toggle-tenant-${tenant.tenant_id}`"
                      icon="pi pi-ban"
                      :label="tenant.disabled ? t('tenants.enableTenant') : t('tenants.disableTenant')"
                      severity="secondary"
                      :loading="tenant.saving"
                      @click="toggleTenantDisabled(tenant)"
                    />
                    <Button
                      :data-testid="`archive-tenant-${tenant.tenant_id}`"
                      icon="pi pi-box"
                      :label="t('tenants.archiveTenant')"
                      severity="danger"
                      outlined
                      :disabled="tenant.archived"
                      :loading="tenant.archiving"
                      @click="archiveTenant(tenant)"
                    />
                    <Message v-if="tenant.error" severity="error" :closable="false">{{ tenant.error }}</Message>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </Card>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import { onMounted, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';

import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiGet, apiPatch, apiPost } from '../services/api';

type AdminTenantResponse = {
  id: string;
  tenant_id: string;
  display_name: string;
  disabled: boolean;
  archived: boolean;
  user_count: number;
  active_admin_count: number;
  created_at: string;
  updated_at: string;
};

type ManagedTenant = AdminTenantResponse & {
  saving: boolean;
  archiving: boolean;
  error: string;
};

const { t } = useI18n();
const router = useRouter();
const loading = ref(false);
const creating = ref(false);
const pageError = ref('');
const createError = ref('');
const notice = ref('');
const tenants = ref<ManagedTenant[]>([]);
const createForm = reactive({
  tenant_id: '',
  display_name: '',
  admin: {
    username: '',
    email: '',
    display_name: '',
    password: '',
  },
});

function resetCreateForm() {
  Object.assign(createForm, {
    tenant_id: '',
    display_name: '',
    admin: {
      username: '',
      email: '',
      display_name: '',
      password: '',
    },
  });
}

function decorateTenant(tenant: AdminTenantResponse): ManagedTenant {
  return {
    ...tenant,
    saving: false,
    archiving: false,
    error: '',
  };
}

function tenantStatusLabel(tenant: AdminTenantResponse): string {
  if (tenant.archived) {
    return t('common.archived');
  }
  if (tenant.disabled) {
    return t('users.disabled');
  }
  return t('common.active');
}

async function loadTenants() {
  loading.value = true;
  pageError.value = '';
  try {
    const payload = await apiGet<{ tenants: AdminTenantResponse[] }>('/api/admin/tenants');
    tenants.value = payload.tenants.map(decorateTenant);
  } catch (exc) {
    pageError.value = exc instanceof Error ? exc.message : t('tenants.loadError');
  } finally {
    loading.value = false;
  }
}

async function createTenant() {
  creating.value = true;
  createError.value = '';
  notice.value = '';
  try {
    const payload = await apiPost<{ tenant: AdminTenantResponse }>('/api/admin/tenants', {
      tenant_id: createForm.tenant_id.trim(),
      display_name: createForm.display_name.trim(),
      admin: {
        username: createForm.admin.username.trim(),
        email: createForm.admin.email.trim(),
        display_name: createForm.admin.display_name.trim(),
        password: createForm.admin.password,
      },
    });
    notice.value = t('tenants.tenantCreated', { tenantId: payload.tenant.tenant_id });
    resetCreateForm();
    await loadTenants();
  } catch (exc) {
    createError.value = exc instanceof Error ? exc.message : t('tenants.createError');
  } finally {
    creating.value = false;
  }
}

function openTenant(tenant: AdminTenantResponse) {
  void router.push({ name: 'tenant-detail', params: { tenantId: tenant.tenant_id } });
}

async function toggleTenantDisabled(tenant: ManagedTenant) {
  tenant.saving = true;
  tenant.error = '';
  notice.value = '';
  try {
    const disabled = !tenant.disabled;
    const payload = await apiPatch<{ tenant: AdminTenantResponse }>(
      `/api/admin/tenants/${encodeURIComponent(tenant.tenant_id)}`,
      { disabled },
    );
    notice.value = disabled
      ? t('tenants.tenantDisabled', { tenantId: payload.tenant.tenant_id })
      : t('tenants.tenantEnabled', { tenantId: payload.tenant.tenant_id });
    await loadTenants();
  } catch (exc) {
    tenant.error = exc instanceof Error ? exc.message : t('tenants.updateError');
  } finally {
    tenant.saving = false;
  }
}

async function archiveTenant(tenant: ManagedTenant) {
  tenant.archiving = true;
  tenant.error = '';
  notice.value = '';
  try {
    const payload = await apiPatch<{ tenant: AdminTenantResponse }>(
      `/api/admin/tenants/${encodeURIComponent(tenant.tenant_id)}`,
      { archived: true },
    );
    notice.value = t('tenants.tenantArchived', { tenantId: payload.tenant.tenant_id });
    await loadTenants();
  } catch (exc) {
    tenant.error = exc instanceof Error ? exc.message : t('tenants.updateError');
  } finally {
    tenant.archiving = false;
  }
}

onMounted(loadTenants);
</script>
