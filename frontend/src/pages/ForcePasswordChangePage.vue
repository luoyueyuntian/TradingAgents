<template>
  <section class="uno-flex uno-min-h-screen uno-items-center uno-justify-center uno-bg-[#f6f7f7] uno-p-5">
    <Card class="uno-w-full uno-max-w-[460px]">
      <template #title>{{ t('auth.changePasswordTitle') }}</template>
      <template #content>
        <form class="uno-grid uno-gap-4" @submit.prevent="submitPasswordChange">
          <Message severity="warn" :closable="false">
            {{ t('auth.changePasswordRequired') }}
          </Message>

          <div class="uno-grid uno-gap-2">
            <label class="uno-text-sm uno-font-600" for="current-password">{{ t('auth.currentPassword') }}</label>
            <InputText
              id="current-password"
              v-model="currentPassword"
              type="password"
              autocomplete="current-password"
              :placeholder="t('auth.passwordPlaceholder')"
            />
          </div>

          <div class="uno-grid uno-gap-2">
            <label class="uno-text-sm uno-font-600" for="new-password">{{ t('auth.newPassword') }}</label>
            <InputText
              id="new-password"
              v-model="newPassword"
              type="password"
              autocomplete="new-password"
              :placeholder="t('auth.newPasswordPlaceholder')"
            />
          </div>

          <Message v-if="session.state.error" severity="error" :closable="false">
            {{ session.state.error }}
          </Message>

          <Button :label="t('auth.changePasswordAction')" type="submit" :loading="session.state.loading" />
        </form>
      </template>
    </Card>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import { ref } from 'vue';
import { useRouter } from 'vue-router';

import { useI18n } from '../i18n';
import { useSession } from '../stores/session';

const router = useRouter();
const session = useSession();
const { t } = useI18n();
const currentPassword = ref('');
const newPassword = ref('');

async function submitPasswordChange() {
  try {
    await session.changePassword(currentPassword.value, newPassword.value);
    await router.push('/');
  } catch {
    // Store error state is rendered in the form.
  }
}
</script>
