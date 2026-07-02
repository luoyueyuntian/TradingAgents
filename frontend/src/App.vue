<template>
  <div v-if="bootstrapping" class="uno-flex uno-min-h-screen uno-items-center uno-justify-center uno-bg-[#f6f7f7] uno-text-[#486164]">
    {{ t('auth.loadingSession') }}
  </div>
  <AppLayout v-else-if="session.state.currentUser && !session.mustChangePassword.value" />
  <RouterView v-else />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { RouterView } from 'vue-router';

import { useI18n } from './i18n';
import AppLayout from './layout/AppLayout.vue';
import { useSession } from './stores/session';

const session = useSession();
const { t } = useI18n();
const bootstrapping = ref(true);

onMounted(async () => {
  try {
    await session.loadCurrentUser();
  } catch {
    // Unauthenticated sessions render the login route.
  } finally {
    bootstrapping.value = false;
  }
});
</script>
