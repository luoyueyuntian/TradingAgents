<template>
  <div v-if="bootstrapping || enteringAuthenticatedView" data-testid="auth-transition" role="status" aria-live="polite" class="uno-flex uno-min-h-screen uno-flex-col uno-items-center uno-justify-center uno-gap-4 uno-bg-[#fafafa] uno-text-[#525252]">
    <template v-if="navigationError">
      <p>{{ t('auth.pageLoadError') }}</p>
      <Button :label="t('common.reload')" @click="retryNavigation" />
    </template>
    <template v-else>{{ t(enteringAuthenticatedView ? 'auth.enteringWorkspace' : 'auth.loadingSession') }}</template>
  </div>
  <AppLayout v-else-if="session.state.currentUser && !session.mustChangePassword.value" />
  <RouterView v-else />
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { RouterView, useRoute, useRouter } from 'vue-router';

import { useI18n } from './i18n';
import AppLayout from './layout/AppLayout.vue';
import { useSession } from './stores/session';

const session = useSession();
const route = useRoute();
const router = useRouter();
const navigationError = ref(false);
const { t } = useI18n();
// Login submission keeps its existing form mounted. Only session bootstrap
// outside the login route replaces the view with a loading placeholder.
const bootstrapping = computed(() => session.state.loading && !session.state.currentUser && route.path !== '/login');
// Authentication updates the store before Vue Router finishes lazy loading.
// Never mount the authenticated layout around an old authentication form.
const enteringAuthenticatedView = computed(() => Boolean(session.state.currentUser) && (
  route.path === '/login' || (route.path === '/change-password' && !session.mustChangePassword.value)
));
watch(enteringAuthenticatedView, (entering) => { if (!entering) navigationError.value = false; });
const stopNavigationErrorHandler = router.onError(() => {
  if (enteringAuthenticatedView.value) navigationError.value = true;
});
onBeforeUnmount(stopNavigationErrorHandler);
function retryNavigation() {
  window.location.replace(session.mustChangePassword.value ? '/change-password' : '/');
}
</script>
