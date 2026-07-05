<template>
  <section class="uno-flex uno-min-h-screen uno-items-center uno-justify-center uno-bg-[#f6f7f7] uno-p-5">
    <Card class="uno-w-full uno-max-w-[420px]">
      <template #title>{{ t('auth.loginTitle') }}</template>
      <template #content>
        <form class="uno-grid uno-gap-4" @submit.prevent="submitLogin">
          <div class="uno-grid uno-gap-2">
            <label class="uno-text-sm uno-font-600" for="login-tenant">{{ t('auth.tenantName') }}</label>
            <InputText
              id="login-tenant"
              v-model="tenantId"
              autocomplete="organization"
              :placeholder="t('auth.tenantPlaceholder')"
            />
          </div>

          <div class="uno-grid uno-gap-2">
            <label class="uno-text-sm uno-font-600" for="login-identifier">{{ t('auth.identifier') }}</label>
            <InputText
              id="login-identifier"
              v-model="identifier"
              autocomplete="username"
              :placeholder="t('auth.identifierPlaceholder')"
            />
          </div>

          <div class="uno-grid uno-gap-2">
            <label class="uno-text-sm uno-font-600" for="login-password">{{ t('auth.password') }}</label>
            <InputText
              id="login-password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              :placeholder="t('auth.passwordPlaceholder')"
            />
          </div>

          <Message v-if="session.state.error" severity="error" :closable="false">
            {{ session.state.error }}
          </Message>

          <div class="uno-flex uno-items-center uno-gap-3">
            <Button :label="t('auth.loginAction')" type="submit" :loading="session.state.loading" />
          </div>
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
const tenantId = ref('');
const identifier = ref('');
const password = ref('');

async function submitLogin() {
  try {
    await session.login(tenantId.value, identifier.value, password.value);
    await router.push(session.mustChangePassword.value ? '/change-password' : '/');
  } catch {
    // Store error state is rendered in the form.
  }
}
</script>
