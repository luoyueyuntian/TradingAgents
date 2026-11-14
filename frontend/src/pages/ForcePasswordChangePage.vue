<template>
  <section :class="embedded ? '' : 'uno-flex uno-min-h-screen uno-items-center uno-justify-center uno-bg-[#f6f7f7] uno-p-5'">
    <Card :class="embedded ? 'uno-w-full' : 'uno-w-full uno-max-w-[460px]'">
      <template #title>{{ t('auth.changePasswordTitle') }}</template>
      <template #content>
        <form class="uno-grid uno-gap-4" @submit.prevent="submitPasswordChange">
          <Message v-if="session.mustChangePassword.value" severity="warn" :closable="false">
            {{ t('auth.changePasswordRequired') }}
          </Message>

          <div class="uno-grid uno-gap-2 uno-text-sm" data-testid="password-change-tips">
            <p>{{ t('auth.sessionPasswordTip') }}</p>
            <p id="new-password-tip">{{ t('auth.newPasswordRules') }}</p>
          </div>

          <div class="uno-grid uno-gap-2">
            <label class="uno-text-sm uno-font-600" for="new-password">{{ t('auth.newPassword') }}</label>
            <InputText
              id="new-password"
              v-model="newPassword"
              type="password"
              autocomplete="new-password"
              :placeholder="t('auth.newPasswordPlaceholder')"
              aria-describedby="new-password-tip"
            />
          </div>

          <div class="uno-grid uno-gap-2">
            <label class="uno-text-sm uno-font-600" for="confirm-password">{{ t('auth.confirmPassword') }}</label>
            <InputText id="confirm-password" v-model="confirmPassword" type="password" autocomplete="new-password" :placeholder="t('auth.confirmPasswordPlaceholder')" />
          </div>

          <Message v-if="success" severity="success" :closable="false" role="status">{{ success }}</Message>
          <Message v-if="feedback" role="alert" aria-live="polite" severity="error" :closable="false">
            {{ feedback }}
          </Message>

          <Button v-if="!embedded && !session.mustChangePassword.value" :label="t('common.cancel')" severity="secondary" @click="router.push('/')" />
          <Button :label="t('auth.changePasswordAction')" type="submit" :loading="session.state.loading" :disabled="session.state.loading" />
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
import { passwordChangeErrorKey } from './passwordChangeFeedback';

const props = withDefaults(defineProps<{ embedded?: boolean }>(), { embedded: false });
const emit = defineEmits<{ changed: [] }>();
const router = useRouter();
const session = useSession();
const { t } = useI18n();
const confirmPassword = ref('');
const newPassword = ref('');
const feedback = ref('');
const success = ref('');

async function submitPasswordChange() {
  if (session.state.loading) return;
  feedback.value = '';
  success.value = '';
  if (!newPassword.value.trim()) {
    feedback.value = t('auth.passwordChangeMissingNew');
    return;
  }
  if (newPassword.value !== confirmPassword.value) {
    feedback.value = t('auth.passwordConfirmationMismatch');
    return;
  }
  try {
    await session.changePassword(newPassword.value);
    newPassword.value = ''; confirmPassword.value = '';
    if (props.embedded) {
      success.value = t('profile.passwordSaved'); emit('changed');
    } else {
      await router.push('/');
    }
  } catch (error) {
    feedback.value = t(passwordChangeErrorKey(error));
  }
}
</script>
