<template>
  <section class="uno-grid uno-gap-4">
    <Message v-if="pageError" severity="error" :closable="false">{{ pageError }}</Message>
    <Message v-if="notice" severity="success" :closable="false">{{ notice }}</Message>

    <Card>
      <template #title>{{ t('users.directory') }}</template>
      <template #content>
        <div class="uno-grid uno-gap-3 md:uno-grid-cols-4">
          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('users.filterName') }}</span>
            <InputText v-model="filters.name" data-testid="filter-name" />
          </label>

          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('users.filterEmail') }}</span>
            <InputText v-model="filters.email" data-testid="filter-email" />
          </label>

          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('users.role') }}</span>
            <Select
              v-model="filters.role"
              data-testid="filter-role"
              :options="roleFilterOptions"
              option-label="label"
              option-value="value"
            />
          </label>

          <label class="uno-grid uno-gap-[0.35rem]">
            <span class="uno-text-[#6f8183]">{{ t('users.status') }}</span>
            <Select
              v-model="filters.status"
              data-testid="filter-status"
              :options="statusOptions"
              option-label="label"
              option-value="value"
            />
          </label>
        </div>

        <div class="uno-mt-3 uno-flex uno-flex-wrap uno-gap-2">
          <Button data-testid="search-users" :label="t('common.search')" @click="loadUsers" />
          <Button data-testid="reset-user-filters" :label="t('common.reset')" severity="secondary" @click="resetFilters" />
        </div>
      </template>
    </Card>

    <div class="uno-flex uno-flex-wrap uno-gap-2">
      <Button
        data-testid="open-create-user"
        :label="t('common.add')"
        icon="pi pi-user-plus"
        :disabled="readOnly"
        @click="openCreateDialog"
      />
      <Button
        data-testid="open-bulk-delete"
        :label="t('common.delete')"
        severity="danger"
        outlined
        :disabled="readOnly || !selectedIds.length"
        @click="bulkDeleteVisible = true"
      />
    </div>

    <Card>
      <template #content>
        <div class="uno-overflow-x-auto">
          <table class="uno-min-w-full uno-border-collapse uno-text-sm">
            <thead>
              <tr class="uno-border-b uno-border-[#dce7e7] uno-text-left uno-text-[#6f8183]">
                <th class="uno-px-3 uno-py-2"></th>
                <th class="uno-px-3 uno-py-2">{{ t('users.username') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('users.displayName') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('users.role') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('common.created') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('users.expiresAt') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('users.status') }}</th>
                <th class="uno-px-3 uno-py-2">{{ t('users.actions') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in users" :key="user.id" :data-testid="`user-row-${user.id}`" class="uno-border-b uno-border-[#eef4f4]">
                <td class="uno-px-3 uno-py-3">
                  <input
                    :checked="selectedIds.includes(user.id)"
                    :data-testid="`select-user-${user.id}`"
                    type="checkbox"
                    :disabled="readOnly"
                    @change="toggleSelected(user.id, $event)"
                  >
                </td>
                <td class="uno-px-3 uno-py-3">{{ user.username }}</td>
                <td class="uno-px-3 uno-py-3">{{ user.display_name }}</td>
                <td class="uno-px-3 uno-py-3">{{ user.role }}</td>
                <td class="uno-px-3 uno-py-3">{{ formatDateTime(user.created_at) }}</td>
                <td class="uno-px-3 uno-py-3">{{ user.expires_at ? formatDateTime(user.expires_at) : t('common.notSet') }}</td>
                <td class="uno-px-3 uno-py-3">
                  <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-2">
                    <span>{{ statusLabel(user) }}</span>
                    <Button
                      v-if="!isExpired(user)"
                      :data-testid="`toggle-user-status-${user.id}`"
                      :label="user.disabled ? t('common.enable') : t('users.disableAction')"
                      severity="secondary"
                      text
                      :disabled="readOnly"
                      @click="toggleDisabled(user)"
                    />
                  </div>
                </td>
                <td class="uno-px-3 uno-py-3">
                  <div class="uno-flex uno-flex-wrap uno-gap-2">
                    <Button
                      :data-testid="`edit-user-${user.id}`"
                      :label="t('common.edit')"
                      text
                      :disabled="readOnly"
                      @click="openEditDialog(user)"
                    />
                    <Button
                      :data-testid="`delete-user-${user.id}`"
                      :label="t('common.delete')"
                      severity="danger"
                      text
                      :disabled="readOnly"
                      @click="openDeleteConfirm(user)"
                    />
                    <Button
                      :data-testid="`reset-password-${user.id}`"
                      :label="t('users.resetPassword')"
                      severity="secondary"
                      text
                      :disabled="readOnly"
                      @click="openResetConfirm(user)"
                    />
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </template>
    </Card>

    <UserFormDialog
      v-model:visible="formVisible"
      :mode="formMode"
      :loading="formSubmitting"
      :error="formError"
      :user="formUser"
      @submit="submitForm"
    />

    <PasswordResultDialog
      v-model:visible="passwordVisible"
      :title="t('users.generatedPasswordTitle')"
      :description="passwordDescription"
      :password="generatedPassword"
    />

    <Dialog
      :visible="Boolean(resetTarget)"
      modal
      :header="t('users.resetPassword')"
      :style="{ width: 'min(480px, 94vw)' }"
      @update:visible="handleResetDialogVisible"
    >
      <p>{{ t('users.resetPasswordConfirm', { username: resetTarget?.username || '' }) }}</p>
      <template #footer>
        <div class="uno-flex uno-justify-end uno-gap-2">
          <Button :label="t('common.cancel')" severity="secondary" @click="resetTarget = null" />
          <Button data-testid="confirm-reset-password" :label="t('users.resetPassword')" @click="confirmResetPassword" />
        </div>
      </template>
    </Dialog>

    <Dialog
      :visible="Boolean(deleteTarget)"
      modal
      :header="t('common.delete')"
      :style="{ width: 'min(480px, 94vw)' }"
      @update:visible="handleDeleteDialogVisible"
    >
      <p>{{ t('users.deleteConfirm', { username: deleteTarget?.username || '' }) }}</p>
      <template #footer>
        <div class="uno-flex uno-justify-end uno-gap-2">
          <Button :label="t('common.cancel')" severity="secondary" @click="deleteTarget = null" />
          <Button data-testid="confirm-delete-user" :label="t('common.delete')" severity="danger" @click="confirmDeleteUser" />
        </div>
      </template>
    </Dialog>

    <Dialog
      :visible="bulkDeleteVisible"
      modal
      :header="t('common.delete')"
      :style="{ width: 'min(480px, 94vw)' }"
      @update:visible="bulkDeleteVisible = false"
    >
      <p>{{ t('users.bulkDeleteConfirm', { count: selectedIds.length }) }}</p>
      <template #footer>
        <div class="uno-flex uno-justify-end uno-gap-2">
          <Button :label="t('common.cancel')" severity="secondary" @click="bulkDeleteVisible = false" />
          <Button data-testid="confirm-bulk-delete" :label="t('common.delete')" severity="danger" @click="confirmBulkDelete" />
        </div>
      </template>
    </Dialog>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Select from 'primevue/select';
import { computed, onMounted, reactive, ref } from 'vue';

import { useI18n } from '../i18n';
import { apiDelete, apiGet, apiPatch, apiPost } from '../services/api';
import { formatDateTime, formatDateTimeInputValue } from '../utils/format';
import PasswordResultDialog from './PasswordResultDialog.vue';
import UserFormDialog from './UserFormDialog.vue';

type AdminUserRole = 'viewer' | 'analyst' | 'admin';

type AdminUserResponse = {
  id: string;
  username: string;
  email: string;
  display_name: string;
  role: AdminUserRole;
  tenant_id: string;
  expires_at: number | null;
  disabled: boolean;
  must_change_password: boolean;
  created_at: number;
  updated_at: number;
  last_login_at: number | null;
};

type UserFormPayload = {
  username: string;
  display_name: string;
  email: string;
  role: AdminUserRole;
  expires_at: string;
};

const props = withDefaults(defineProps<{
  listPath: string;
  createPath: string;
  bulkDeletePath: string;
  updatePath: (userId: string) => string;
  deletePath: (userId: string) => string;
  resetPasswordPath: (userId: string) => string;
  readOnly?: boolean;
}>(), {
  readOnly: false,
});

const { t } = useI18n();
const users = ref<AdminUserResponse[]>([]);
const filters = reactive({
  name: '',
  email: '',
  role: '',
  status: 'all',
});
const selectedIds = ref<string[]>([]);
const pageError = ref('');
const notice = ref('');
const formVisible = ref(false);
const formMode = ref<'create' | 'edit'>('create');
const formSubmitting = ref(false);
const formError = ref('');
const editingUser = ref<AdminUserResponse | null>(null);
const passwordVisible = ref(false);
const generatedPassword = ref('');
const passwordDescription = ref('');
const resetTarget = ref<AdminUserResponse | null>(null);
const deleteTarget = ref<AdminUserResponse | null>(null);
const bulkDeleteVisible = ref(false);

const roleFilterOptions = computed(() => [
  { label: t('common.all'), value: '' },
  { label: t('auth.roleViewer'), value: 'viewer' },
  { label: t('auth.roleAnalyst'), value: 'analyst' },
  { label: t('auth.roleAdmin'), value: 'admin' },
]);

const statusOptions = computed(() => [
  { label: t('common.all'), value: 'all' },
  { label: t('users.active'), value: 'active' },
  { label: t('users.disabled'), value: 'disabled' },
  { label: t('users.expired'), value: 'expired' },
]);

const formUser = computed(() => {
  if (!editingUser.value) {
    return {
      username: '',
      display_name: '',
      email: '',
      role: 'viewer' as AdminUserRole,
      expires_at: '',
    };
  }
  return {
    username: editingUser.value.username,
    display_name: editingUser.value.display_name,
    email: editingUser.value.email,
    role: editingUser.value.role,
    expires_at: formatDateTimeInputValue(editingUser.value.expires_at),
  };
});

function buildListPath() {
  const params = new URLSearchParams({
    status: filters.status || 'all',
    deleted_scope: 'active',
  });
  if (filters.name.trim()) {
    params.set('name', filters.name.trim());
  }
  if (filters.email.trim()) {
    params.set('email', filters.email.trim());
  }
  if (filters.role) {
    params.set('role', filters.role);
  }
  return `${props.listPath}?${params.toString()}`;
}

function toApiDateTime(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const date = new Date(trimmed);
  return Number.isNaN(date.getTime()) ? null : date.getTime();
}

function isExpired(user: AdminUserResponse) {
  return user.expires_at !== null && user.expires_at <= Date.now();
}

function statusLabel(user: AdminUserResponse) {
  if (user.disabled) {
    return t('users.disabled');
  }
  if (isExpired(user)) {
    return t('users.expired');
  }
  return t('users.active');
}

function openCreateDialog() {
  editingUser.value = null;
  formMode.value = 'create';
  formError.value = '';
  formVisible.value = true;
}

function openEditDialog(user: AdminUserResponse) {
  editingUser.value = user;
  formMode.value = 'edit';
  formError.value = '';
  formVisible.value = true;
}

function openResetConfirm(user: AdminUserResponse) {
  resetTarget.value = user;
}

function openDeleteConfirm(user: AdminUserResponse) {
  deleteTarget.value = user;
}

function toggleSelected(userId: string, event: Event) {
  const checked = (event.target as HTMLInputElement).checked;
  if (checked) {
    if (!selectedIds.value.includes(userId)) {
      selectedIds.value = [...selectedIds.value, userId];
    }
    return;
  }
  selectedIds.value = selectedIds.value.filter((id) => id !== userId);
}

async function loadUsers() {
  pageError.value = '';
  try {
    const payload = await apiGet<{ users: AdminUserResponse[] }>(buildListPath());
    users.value = payload.users;
    selectedIds.value = selectedIds.value.filter((id) => users.value.some((user) => user.id === id));
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : t('users.loadError');
  }
}

function resetFilters() {
  filters.name = '';
  filters.email = '';
  filters.role = '';
  filters.status = 'all';
  void loadUsers();
}

async function submitForm(payload: UserFormPayload) {
  formSubmitting.value = true;
  formError.value = '';
  try {
    if (formMode.value === 'create') {
      const response = await apiPost<{ user: AdminUserResponse; temporary_password: string }>(
        props.createPath,
        {
          username: payload.username.trim(),
          display_name: payload.display_name.trim(),
          email: payload.email.trim(),
          role: payload.role,
          expires_at: toApiDateTime(payload.expires_at),
        },
      );
      generatedPassword.value = response.temporary_password;
      passwordDescription.value = t('users.generatedPasswordDescription', { username: response.user.username });
      passwordVisible.value = true;
      notice.value = t('users.userCreated', { username: response.user.username });
    } else if (editingUser.value) {
      const response = await apiPatch<{ user: AdminUserResponse }>(
        props.updatePath(editingUser.value.id),
        {
          display_name: payload.display_name.trim(),
          email: payload.email.trim(),
          role: payload.role,
          expires_at: toApiDateTime(payload.expires_at),
        },
      );
      notice.value = t('users.userUpdated', { username: response.user.username });
    }
    formVisible.value = false;
    await loadUsers();
  } catch (error) {
    formError.value = error instanceof Error ? error.message : t('users.updateError');
  } finally {
    formSubmitting.value = false;
  }
}

async function toggleDisabled(user: AdminUserResponse) {
  pageError.value = '';
  try {
    const response = await apiPatch<{ user: AdminUserResponse }>(
      props.updatePath(user.id),
      { disabled: !user.disabled },
    );
    notice.value = response.user.disabled
      ? t('users.userDisabled', { username: response.user.username })
      : t('users.userEnabled', { username: response.user.username });
    await loadUsers();
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : t('users.updateError');
  }
}

async function confirmDeleteUser() {
  if (!deleteTarget.value) {
    return;
  }
  pageError.value = '';
  try {
    await apiDelete(props.deletePath(deleteTarget.value.id));
    notice.value = t('users.userDeleted', { username: deleteTarget.value.username });
    deleteTarget.value = null;
    await loadUsers();
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : t('users.deleteError');
  }
}

async function confirmResetPassword() {
  if (!resetTarget.value) {
    return;
  }
  pageError.value = '';
  try {
    const response = await apiPost<{ user: AdminUserResponse; temporary_password: string }>(
      props.resetPasswordPath(resetTarget.value.id),
      {},
    );
    generatedPassword.value = response.temporary_password;
    passwordDescription.value = t('users.generatedPasswordDescription', { username: response.user.username });
    passwordVisible.value = true;
    notice.value = t('users.passwordResetNotice', { username: response.user.username });
    resetTarget.value = null;
    await loadUsers();
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : t('users.resetError');
  }
}

async function confirmBulkDelete() {
  pageError.value = '';
  try {
    const response = await apiPost<{ deleted_ids: string[]; failed: Array<{ user_id: string; detail: string }> }>(
      props.bulkDeletePath,
      { user_ids: selectedIds.value },
    );
    if (response.failed.length) {
      pageError.value = response.failed.map((item) => item.detail).join('; ');
    } else {
      notice.value = t('users.bulkDeleted', { count: response.deleted_ids.length });
    }
    selectedIds.value = [];
    bulkDeleteVisible.value = false;
    await loadUsers();
  } catch (error) {
    pageError.value = error instanceof Error ? error.message : t('users.deleteError');
  }
}

function handleResetDialogVisible(value: boolean) {
  if (!value) {
    resetTarget.value = null;
  }
}

function handleDeleteDialogVisible(value: boolean) {
  if (!value) {
    deleteTarget.value = null;
  }
}

defineExpose({
  loadUsers,
});

onMounted(() => {
  void loadUsers();
});
</script>
