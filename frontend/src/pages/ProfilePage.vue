<template>
  <section>
    <PageHeader :eyebrow="t('profile.account')" :title="t('profile.title')" :description="t('profile.description')" />
    <Message v-if="error" severity="error" :closable="false" role="alert">{{ error }}</Message>
    <Message v-if="notice" severity="success" :closable="false" role="status">{{ notice }}</Message>
    <Button v-if="!profile" :label="t('common.reload')" :loading="loading" @click="load" />
    <div v-if="profile" class="uno-grid uno-gap-4 lg:uno-grid-cols-2">
      <Card>
        <template #title>{{ t('profile.account') }}</template>
        <template #content>
          <dl class="uno-grid uno-grid-cols-[auto_minmax(0,1fr)] uno-gap-x-5 uno-gap-y-3 uno-text-sm">
            <dt>{{ t('profile.username') }}</dt><dd class="uno-break-all">{{ profile.user.username }}</dd>
            <dt>{{ t('profile.email') }}</dt><dd class="uno-break-all">{{ profile.user.email }}</dd>
            <dt>{{ t('profile.role') }}</dt><dd>{{ profile.user.role }}</dd>
            <dt>{{ t('profile.tenant') }}</dt><dd>{{ profile.user.tenant_id }}</dd>
            <dt>{{ t('profile.created') }}</dt><dd>{{ formatDateTime(profile.created_at) }}</dd>
            <dt>{{ t('profile.passwordUpdated') }}</dt><dd>{{ formatDateTime(profile.password_updated_at) }}</dd>
          </dl>
          <form class="uno-mt-5 uno-grid uno-gap-3" @submit.prevent="saveNickname">
            <label for="profile-nickname">{{ t('profile.nickname') }}</label>
            <InputText id="profile-nickname" v-model="nickname" maxlength="80" required />
            <Button :label="t('common.save')" type="submit" :loading="busy" :disabled="busy" />
          </form>
        </template>
      </Card>
      <Card>
        <template #title>{{ t('profile.emailTitle') }}</template>
        <template #content>
          <p class="uno-mb-4 uno-text-sm uno-text-[#6f8183]">{{ t('profile.emailTip') }}</p>
          <Message v-if="!profile.email_verification_available" severity="warn" :closable="false">{{ t('profile.mailUnavailable') }}</Message>
          <form class="uno-grid uno-gap-3" @submit.prevent="confirmEmail">
            <label for="profile-email">{{ t('profile.newEmail') }}</label>
            <InputText id="profile-email" v-model="email" type="email" :disabled="busy || !profile.email_verification_available" />
            <Button :label="t('profile.sendCode')" :loading="busy" :disabled="busy || cooldown > 0 || !email.trim() || !profile.email_verification_available" @click="requestEmail" />
            <p v-if="cooldown" class="uno-text-sm" role="status">{{ t('profile.resendWait', { seconds: cooldown }) }}</p>
            <p v-if="sentTo" class="uno-text-sm" role="status">{{ t('profile.sentTo', { email: sentTo }) }}</p>
            <label for="profile-code">{{ t('profile.code') }}</label>
            <InputText id="profile-code" v-model="code" inputmode="numeric" autocomplete="one-time-code" maxlength="6" :disabled="busy || !sentTo" />
            <Button :label="t('profile.confirmEmail')" type="submit" :loading="busy" :disabled="busy || !sentTo || code.length !== 6" />
          </form>
        </template>
      </Card>
      <div id="password" class="uno-scroll-mt-24"><ForcePasswordChangePage embedded @changed="load" /></div>
      <Card>
        <template #title>{{ t('profile.sessions') }}</template>
        <template #content>
          <p class="uno-mb-4 uno-text-sm uno-text-[#6f8183]">{{ t('profile.sessionsTip') }}</p>
          <ul class="uno-grid uno-gap-3">
            <li v-for="(item, index) in profile.sessions" :key="index" class="uno-rounded-lg uno-border uno-border-[#dce7e7] uno-p-3 uno-text-sm">
              <strong>{{ item.current ? t('profile.currentSession') : t('profile.otherSession') }}</strong>
              <p>{{ t('profile.loginTime') }}：{{ formatDateTime(item.created_at) }}</p>
              <p>{{ t('profile.lastSeen') }}：{{ formatDateTime(item.last_seen_at) }}</p>
              <p>{{ t('profile.expires') }}：{{ formatDateTime(item.expires_at) }}</p>
            </li>
          </ul>
          <Button class="uno-mt-4" :label="t('profile.revokeOthers')" severity="secondary" :loading="busy" :disabled="busy || !profile.sessions.some((item: JsonRecord) => !item.current)" @click="revokeOthers" />
        </template>
      </Card>
      <Card>
        <template #title>{{ t('profile.preferences') }}</template>
        <template #content>
          <label class="uno-grid uno-gap-3" for="profile-language">
            {{ t('profile.language') }}
            <Select id="profile-language" v-model="locale" :options="locales" option-label="label" option-value="value" />
          </label>
          <p class="uno-mt-3 uno-text-sm uno-text-[#6f8183]">{{ t('profile.languageTip') }}</p>
        </template>
      </Card>
    </div>
  </section>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import Card from 'primevue/card';
import InputText from 'primevue/inputtext';
import Message from 'primevue/message';
import Select from 'primevue/select';
import { onMounted, onUnmounted, ref, watch } from 'vue';

import PageHeader from '../components/PageHeader.vue';
import { useI18n } from '../i18n';
import { apiGet, apiPost, apiPut } from '../services/api';
import { useSession } from '../stores/session';
import { formatDateTime, type JsonRecord } from '../utils/format';
import ForcePasswordChangePage from './ForcePasswordChangePage.vue';

const { t, locale, locales } = useI18n();
const session = useSession();
const profile = ref<JsonRecord | null>(null);
const nickname = ref('');
const email = ref('');
const code = ref('');
const sentTo = ref('');
const cooldown = ref(0);
const loading = ref(false);
const busy = ref(false);
const error = ref('');
const notice = ref('');
let timer: ReturnType<typeof setInterval> | undefined;
watch(email, () => {
  if (sentTo.value) {
    sentTo.value = ''; code.value = '';
    notice.value = t('profile.emailTargetChanged');
  }
});
async function load() {
  loading.value = true;
  try {
    profile.value = await apiGet<JsonRecord>('/api/auth/profile', {});
    nickname.value = String(profile.value.user.display_name || '');
  } catch (exc) { error.value = exc instanceof Error ? exc.message : t('profile.failed'); }
  finally { loading.value = false; }
}
async function perform(action: () => Promise<void>) {
  if (busy.value) return;
  busy.value = true; error.value = ''; notice.value = '';
  try { await action(); }
  catch (exc) { error.value = exc instanceof Error ? exc.message : t('profile.failed'); }
  finally { busy.value = false; }
}
function saveNickname() {
  return perform(async () => {
    if (!nickname.value.trim()) throw new Error(t('profile.nicknameRequired'));
    await apiPut('/api/auth/profile', { display_name: nickname.value.trim() }, {});
    await session.loadCurrentUser(); await load(); notice.value = t('profile.saved');
  });
}
function requestEmail() {
  return perform(async () => {
    const target = email.value.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(target)) throw new Error(t('profile.emailInvalid'));
    await apiPost('/api/auth/profile/email/request', { email: target }, {});
    sentTo.value = target; code.value = ''; cooldown.value = 60;
    if (timer) clearInterval(timer);
    timer = setInterval(() => { if (cooldown.value > 0) cooldown.value--; else if (timer) clearInterval(timer); }, 1000);
    notice.value = t('profile.codeSent');
  });
}
function confirmEmail() {
  return perform(async () => {
    await apiPost('/api/auth/profile/email/confirm', { code: code.value.trim() }, {});
    await session.loadCurrentUser(); await load(); code.value = ''; sentTo.value = ''; email.value = '';
    notice.value = t('profile.emailUpdated');
  });
}
function revokeOthers() {
  return perform(async () => {
    await apiPost('/api/auth/profile/sessions/revoke-others', {}, {});
    await load(); notice.value = t('profile.sessionsRevoked');
  });
}
onMounted(load);
onUnmounted(() => { if (timer) clearInterval(timer); });
</script>
