<template>
  <section class="uno-flex uno-min-h-screen uno-items-center uno-justify-center uno-bg-[#fafafa] uno-p-5">
    <Card class="uno-w-full uno-max-w-[420px]">
      <template #title>
        <div v-if="guestMode" class="uno-grid uno-grid-cols-[1fr_auto_1fr] uno-items-center">
          <Button data-testid="guest-login-back" icon="pi pi-angle-left" :label="t('common.back')" text severity="secondary" size="small" class="uno-justify-self-start" :disabled="session.state.loading" @click="setMode(false)" />
          <span aria-live="polite" class="uno-text-center">{{ t('guest.loginTitle') }}</span>
        </div>
        <template v-else>
        <div class="uno-mb-4 uno-flex uno-items-center uno-gap-3">
          <img :src="'/static/icons/tradingagents-ta-vermilion.svg'" alt="" aria-hidden="true" width="40" height="40" />
          <span class="uno-text-xl uno-font-bold uno-text-[#262626]">TradingAgents</span>
        </div>
        <span aria-live="polite">{{ t('auth.loginTitle') }}</span>
        </template>
      </template>
      <template #content>
        <Message v-if="guestMode" severity="info" :closable="false" class="uno-mb-4" data-testid="guest-view-scope">{{ t('guest.viewScope') }}</Message>
        <form class="uno-grid uno-gap-4" @submit.prevent="submitLogin">
          <div class="uno-grid uno-gap-2">
            <label class="uno-text-sm uno-font-600" for="login-identifier">{{ guestMode ? t('users.username') : t('auth.identifier') }}</label>
            <InputText v-if="guestMode" id="login-identifier" class="guest-credential" :model-value="guest?.username || ''" disabled readonly autocomplete="off" />
            <InputText v-else id="login-identifier" v-model="identifier" autocomplete="username" :placeholder="t('auth.identifierPlaceholder')" :disabled="session.state.loading" />
          </div>
          <div class="uno-grid uno-gap-2">
            <label class="uno-text-sm uno-font-600" for="login-password">{{ t('auth.password') }}</label>
            <InputText v-if="guestMode" id="login-password" class="guest-credential" :model-value="guest?.password || ''" type="password" disabled readonly autocomplete="off" />
            <InputText v-else id="login-password" v-model="password" type="password" autocomplete="current-password" :placeholder="t('auth.passwordPlaceholder')" :disabled="session.state.loading" />
          </div>
          <Message v-if="session.state.error" severity="error" :closable="false">{{ session.state.error }}</Message>
          <Button fluid :label="t('auth.loginAction')" type="submit" :loading="session.state.loading" :disabled="session.state.loading" />
        </form>
        <Button v-if="!guestMode && guest" data-testid="guest-login-entry" fluid class="uno-mt-3" :label="t('guest.signIn')" severity="secondary" :disabled="session.state.loading" @click="setMode(true)" />
      </template>
    </Card>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

import { useI18n } from '../i18n';
import { useSession } from '../stores/session';
import { apiGet } from '../services/api';

const router = useRouter();
const session = useSession();
const { t } = useI18n();
const identifier = ref('');
const password = ref('');
const guestMode = ref(false);
const guest = ref<{ username: string; password: string; tenant_id: string } | null>(null);
onMounted(async () => {
  try { guest.value = await apiGet('/api/auth/guest', {}); }
  catch { guest.value = null; }
});
function setMode(value: boolean) {
  if (session.state.loading || (value && !guest.value)) return;
  session.state.error = '';
  guestMode.value = value;
}
async function submitLogin() {
  if (session.state.loading || (guestMode.value && !guest.value)) return;
  try {
    const loginIdentifier = guestMode.value ? guest.value!.username : identifier.value;
    const loginPassword = guestMode.value ? guest.value!.password : password.value;
    await session.login(loginIdentifier, loginPassword);
    await router.push(session.mustChangePassword.value ? '/change-password' : '/');
  } catch {
    // Store error state is rendered in the form.
  }
}
</script>

<style scoped>
.guest-credential:disabled {
  background: #e5e5e5;
  border-color: #d4d4d4;
  color: #737373;
  -webkit-text-fill-color: #737373;
  opacity: 1;
  cursor: not-allowed;
}
</style>
