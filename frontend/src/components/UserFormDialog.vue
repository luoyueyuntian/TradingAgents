<template>
  <Dialog
    :visible="visible"
    modal
    :header="existingAccount ? t('users.addExistingAccount') : mode === 'create' ? t('users.createUser') : t('common.edit')"
    :style="{ width: 'min(640px, 94vw)' }"
    @update:visible="emit('update:visible', $event)"
  >
    <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>
    <div class="uno-grid uno-gap-4">
      <label v-if="!existingAccount" class="uno-grid uno-gap-[0.35rem]">
        <span class="uno-text-[#6f8183]">{{ t('users.username') }}</span>
        <InputText
          v-model="form.username"
          data-testid="user-form-username"
          :readonly="mode === 'edit'"
          :disabled="loading"
        />
      </label>

      <label v-if="!existingAccount" class="uno-grid uno-gap-[0.35rem]">
        <span class="uno-text-[#6f8183]">{{ t('users.displayName') }}</span>
        <InputText
          v-model="form.display_name"
          data-testid="user-form-display-name"
          :readonly="mode === 'edit'"
          :disabled="loading"
        />
      </label>

      <label class="uno-grid uno-gap-[0.35rem]">
        <span class="uno-text-[#6f8183]">{{ t('users.email') }}</span>
        <InputText
          v-model="form.email"
          data-testid="user-form-email"
          :readonly="mode === 'edit'"
          type="email"
          :disabled="loading"
        />
      </label>

      <label class="uno-grid uno-gap-[0.35rem]">
        <span class="uno-text-[#6f8183]">{{ t('users.role') }}</span>
        <Select
          v-model="form.role"
          data-testid="user-form-role"
          :options="roleOptions"
          option-label="label"
          option-value="value"
          :disabled="loading"
        />
      </label>

      <label class="uno-grid uno-gap-[0.35rem]">
        <span class="uno-text-[#6f8183]">{{ t('users.expiresAt') }}</span>
        <DateTimeInput
          v-model="form.expires_at"
          data-testid="user-form-expires-at"
          mode="datetime"
          :disabled="loading"
        />
      </label>
    </div>

    <template #footer>
      <div class="uno-flex uno-justify-end uno-gap-2">
        <Button :label="t('common.cancel')" severity="secondary" @click="emit('update:visible', false)" />
        <Button
          data-testid="submit-user-form"
          :label="mode === 'create' ? t('users.createAction') : t('common.save')"
          :loading="loading"
          @click="submit"
        />
      </div>
    </template>
  </Dialog>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Select from 'primevue/select';
import { computed, reactive, watch } from 'vue';

import DateTimeInput from './DateTimeInput.vue';
import { useI18n } from '../i18n';

type AdminUserRole = 'viewer' | 'analyst' | 'admin';

type UserFormValue = {
  username: string;
  display_name: string;
  email: string;
  role: AdminUserRole;
  expires_at: string;
};

const props = withDefaults(defineProps<{
  visible: boolean;
  mode: 'create' | 'edit';
  existingAccount?: boolean;
  loading?: boolean;
  error?: string;
  user?: Partial<UserFormValue> | null;
}>(), {
  loading: false,
  error: '',
  user: null,
});

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void;
  (e: 'submit', value: UserFormValue): void;
}>();

const { t } = useI18n();
const form = reactive<UserFormValue>({
  username: '',
  display_name: '',
  email: '',
  role: 'viewer',
  expires_at: '',
});

const roleOptions = computed(() => [
  { label: t('auth.roleViewer'), value: 'viewer' },
  { label: t('auth.roleAnalyst'), value: 'analyst' },
  { label: t('auth.roleAdmin'), value: 'admin' },
]);

function syncForm() {
  Object.assign(form, {
    username: props.user?.username || '',
    display_name: props.user?.display_name || '',
    email: props.user?.email || '',
    role: (props.user?.role || 'viewer') as AdminUserRole,
    expires_at: props.user?.expires_at || '',
  });
}

function submit() {
  emit('submit', {
    username: form.username,
    display_name: form.display_name,
    email: form.email,
    role: form.role,
    expires_at: form.expires_at,
  });
}

watch(() => [props.visible, props.mode, props.user], () => {
  syncForm();
}, { immediate: true });
</script>
