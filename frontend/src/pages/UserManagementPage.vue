<template>
  <section class="uno-grid uno-gap-4">
    <PageHeader
      :eyebrow="t('users.eyebrow')"
      :title="t('users.title')"
      :description="t('users.description')"
    >
      <template #actions>
        <Button icon="pi pi-refresh" :label="t('common.refresh')" severity="secondary" :loading="loading" @click="loadUsers" />
      </template>
    </PageHeader>

    <Message v-if="pageError" severity="error" :closable="false">{{ pageError }}</Message>
    <Message v-if="notice" severity="success" :closable="false">{{ notice }}</Message>

    <Card>
      <template #title>{{ t('users.createUser') }}</template>
      <template #content>
        <div class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(180px,1fr))] uno-gap-3">
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('users.username') }}</span>
            <InputText v-model="createForm.username" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('users.email') }}</span>
            <InputText v-model="createForm.email" type="email" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('users.displayName') }}</span>
            <InputText v-model="createForm.display_name" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('users.role') }}</span>
            <Select v-model="createForm.role" :options="roleOptions" option-label="label" option-value="value" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('users.tempPassword') }}</span>
            <InputText v-model="createForm.password" type="password" />
          </label>
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('users.expiresAt') }}</span>
            <InputText v-model="createForm.expires_at" type="datetime-local" />
          </label>
        </div>
        <Message v-if="createError" severity="error" :closable="false" class="uno-mt-3">{{ createError }}</Message>
        <div class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-gap-[0.55rem]">
          <Button
            data-testid="create-user-submit"
            icon="pi pi-user-plus"
            :label="t('users.createAction')"
            :loading="creating"
            @click="createUser"
          />
        </div>
      </template>
    </Card>

    <Card>
      <template #title>{{ t('users.directory') }}</template>
      <template #content>
        <div class="uno-overflow-x-auto">
          <table class="uno-min-w-full uno-border-collapse uno-text-sm">
            <thead>
              <tr class="uno-border-b uno-border-[#dce7e7] uno-text-left uno-text-[#6f8183]">
                <th class="uno-px-3 uno-py-2">{{ t('users.user') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('users.role') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('users.expiresAt') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('users.status') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('users.resetPassword') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('users.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.id" class="uno-border-b uno-border-[#eef4f4]">
                <td class="uno-px-3 uno-py-3 uno-align-top">
                  <div class="uno-grid uno-gap-1">
                    <strong class="uno-break-words uno-text-[#132a2d]">{{ user.username }}</strong>
                    <span class="uno-break-words">{{ user.email }}</span>
                    <InputText v-model="user.draftDisplayName" />
                  </div>
                </td>
                <td class="uno-px-3 uno-py-3 uno-align-top">
                  <Select v-model="user.draftRole" :options="roleOptions" option-label="label" option-value="value" class="uno-min-w-[8rem]" />
                </td>
                <td class="uno-px-3 uno-py-3 uno-align-top">
                  <InputText v-model="user.draftExpiresAt" type="datetime-local" />
                </td>
                <td class="uno-px-3 uno-py-3 uno-align-top">
                  <label class="uno-flex uno-items-center uno-gap-2">
                    <input v-model="user.draftDisabled" type="checkbox">
                    <span>{{ user.draftDisabled ? t('users.disabled') : t('users.active') }}</span>
                  </label>
                </td>
                <td class="uno-px-3 uno-py-3 uno-align-top">
                  <div class="uno-grid uno-gap-2">
                    <InputText v-model="user.resetPassword" type="password" :placeholder="t('users.newPasswordPlaceholder')" />
                    <Button
                      icon="pi pi-key"
                      :label="t('users.resetPassword')"
                      severity="secondary"
                      :disabled="!user.resetPassword.trim()"
                      @click="resetPassword(user)"
                    />
                  </div>
                </td>
                <td class="uno-px-3 uno-py-3 uno-align-top">
                  <div class="uno-grid uno-gap-2">
                    <Button icon="pi pi-save" :label="t('common.save')" :loading="user.saving" @click="updateUser(user)" />
                    <Button icon="pi pi-trash" :label="t('common.delete')" severity="danger" outlined :loading="user.removing" @click="deleteUser(user)" />
                    <Message v-if="user.error" severity="error" :closable="false">{{ user.error }}</Message>
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
import Select from 'primevue/select';
import { computed, onMounted, reactive, ref } from 'vue';

import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPatch, apiPost } from '../services/api';
import { useSession } from '../stores/session';

type AdminUserRole = 'viewer' | 'analyst' | 'admin';

type AdminUserResponse = {
  id: string;
  username: string;
  email: string;
  display_name: string;
  role: AdminUserRole;
  tenant_id: string;
  expires_at: string | null;
  must_change_password: boolean;
  disabled: boolean;
};

type ManagedUser = AdminUserResponse & {
  draftDisplayName: string;
  draftRole: AdminUserRole;
  draftExpiresAt: string;
  draftDisabled: boolean;
  resetPassword: string;
  saving: boolean;
  removing: boolean;
  error: string;
};

const session = useSession();
const { t } = useI18n();
const loading = ref(false);
const creating = ref(false);
const pageError = ref('');
const createError = ref('');
const notice = ref('');
const users = ref<ManagedUser[]>([]);
const createForm = reactive({
  username: '',
  email: '',
  display_name: '',
  role: 'viewer' as AdminUserRole,
  password: '',
  expires_at: '',
});

const roleOptions = computed(() => [
  { label: t('auth.roleViewer'), value: 'viewer' },
  { label: t('auth.roleAnalyst'), value: 'analyst' },
  { label: t('auth.roleAdmin'), value: 'admin' },
]);

function toLocalDateTime(value: string | null): string {
  if (!value) {
    return '';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return '';
  }
  const localDate = new Date(date.getTime() - (date.getTimezoneOffset() * 60_000));
  return localDate.toISOString().slice(0, 16);
}

function toApiDateTime(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const date = new Date(trimmed);
  return Number.isNaN(date.getTime()) ? trimmed : date.toISOString();
}

function decorateUser(user: AdminUserResponse): ManagedUser {
  return {
    ...user,
    draftDisplayName: user.display_name || '',
    draftRole: user.role,
    draftExpiresAt: toLocalDateTime(user.expires_at),
    draftDisabled: user.disabled,
    resetPassword: '',
    saving: false,
    removing: false,
    error: '',
  };
}

function resetCreateForm() {
  Object.assign(createForm, {
    username: '',
    email: '',
    display_name: '',
    role: 'viewer',
    password: '',
    expires_at: '',
  });
}

async function loadUsers() {
  loading.value = true;
  pageError.value = '';
  try {
    const payload = await apiGet<{ users: AdminUserResponse[] }>('/api/admin/users', session.apiContext.value);
    users.value = payload.users.map(decorateUser);
  } catch (exc) {
    pageError.value = exc instanceof Error ? exc.message : t('users.loadError');
  } finally {
    loading.value = false;
  }
}

async function createUser() {
  creating.value = true;
  createError.value = '';
  notice.value = '';
  try {
    const payload = await apiPost<{ user: AdminUserResponse }>('/api/admin/users', {
      username: createForm.username.trim(),
      email: createForm.email.trim(),
      display_name: createForm.display_name.trim(),
      role: createForm.role,
      password: createForm.password,
      expires_at: toApiDateTime(createForm.expires_at),
    }, session.apiContext.value);
    notice.value = t('users.userCreated', { username: payload.user.username });
    resetCreateForm();
    await loadUsers();
  } catch (exc) {
    createError.value = exc instanceof Error ? exc.message : t('users.createError');
  } finally {
    creating.value = false;
  }
}

async function updateUser(user: ManagedUser) {
  user.saving = true;
  user.error = '';
  notice.value = '';
  try {
    const payload = await apiPatch<{ user: AdminUserResponse }>(`/api/admin/users/${encodeURIComponent(user.id)}`, {
      display_name: user.draftDisplayName.trim(),
      role: user.draftRole,
      expires_at: toApiDateTime(user.draftExpiresAt),
      disabled: user.draftDisabled,
    }, session.apiContext.value);
    notice.value = t('users.userUpdated', { username: payload.user.username });
    await loadUsers();
  } catch (exc) {
    user.error = exc instanceof Error ? exc.message : t('users.updateError');
  } finally {
    user.saving = false;
  }
}

async function resetPassword(user: ManagedUser) {
  user.saving = true;
  user.error = '';
  notice.value = '';
  try {
    const payload = await apiPatch<{ user: AdminUserResponse }>(`/api/admin/users/${encodeURIComponent(user.id)}`, {
      password: user.resetPassword,
    }, session.apiContext.value);
    notice.value = t('users.passwordResetNotice', { username: payload.user.username });
    await loadUsers();
  } catch (exc) {
    user.error = exc instanceof Error ? exc.message : t('users.resetError');
  } finally {
    user.saving = false;
  }
}

async function deleteUser(user: ManagedUser) {
  user.removing = true;
  user.error = '';
  notice.value = '';
  try {
    await apiDelete<{ user: AdminUserResponse }>(`/api/admin/users/${encodeURIComponent(user.id)}`, session.apiContext.value);
    notice.value = t('users.userDisabled', { username: user.username });
    await loadUsers();
  } catch (exc) {
    user.error = exc instanceof Error ? exc.message : t('users.deleteError');
  } finally {
    user.removing = false;
  }
}

onMounted(loadUsers);
</script>
