<template>
  <RouterLink v-if="tenant" to="/notifications" data-testid="notification-bell" :aria-label="label" :title="label" class="uno-relative uno-inline-flex uno-h-10 uno-w-10 uno-shrink-0 uno-items-center uno-justify-center uno-rounded-full uno-text-[#525252] hover:uno-bg-[#f5f5f5] focus-visible:uno-outline-2 focus-visible:uno-outline-offset-2">
    <i class="pi pi-bell uno-text-lg" aria-hidden="true" />
    <span v-if="unreadBadge" data-testid="notification-badge" aria-hidden="true" class="notification-count">{{ unreadBadge }}</span>
  </RouterLink>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, watch } from 'vue';
import { RouterLink, useRoute } from 'vue-router';
import { useI18n } from '../i18n';
import { useSession } from '../stores/session';
import { activateNotificationScope, clearUnread, refreshUnread, unreadBadge, unreadCount } from '../stores/notifications';
const session = useSession();
const route = useRoute();
const { t } = useI18n();
const tenant = computed(() => session.apiContext.value.tenantId || '');
const label = computed(() => unreadCount.value === null ? t('messages.title') : t('messages.bellLabel', { count: unreadCount.value }));
function refresh() { if (document.visibilityState !== 'hidden') void refreshUnread({ ...session.apiContext.value }); }
watch(tenant, (value) => { activateNotificationScope(value); refresh(); }, { immediate: true });
watch(() => route.fullPath, refresh);
let timer: ReturnType<typeof setInterval> | undefined;
onMounted(() => {
  timer = setInterval(refresh, 30000);
  window.addEventListener('focus', refresh);
  document.addEventListener('visibilitychange', refresh);
});
onBeforeUnmount(() => {
  if (timer) clearInterval(timer);
  window.removeEventListener('focus', refresh);
  document.removeEventListener('visibilitychange', refresh);
  clearUnread();
});
</script>
<style scoped>
.notification-count {
  position: absolute;
  top: 0;
  right: -4px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 19px;
  height: 19px;
  padding: 0 4px;
  border: 2px solid white;
  border-radius: 999px;
  background: var(--p-primary-color);
  color: white;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  pointer-events: none;
}
</style>
