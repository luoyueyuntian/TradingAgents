<template>
  <div v-if="bootstrapping" class="uno-flex uno-min-h-screen uno-items-center uno-justify-center uno-bg-[#f6f7f7] uno-text-[#486164]">
    {{ t('auth.loadingSession') }}
  </div>
  <AppLayout v-else-if="session.state.currentUser && !session.mustChangePassword.value" />
  <RouterView v-else />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RouterView } from 'vue-router';

import { useI18n } from './i18n';
import AppLayout from './layout/AppLayout.vue';
import { useSession } from './stores/session';

const session = useSession();
const { t } = useI18n();
const bootstrapping = computed(() => session.state.loading && !session.state.currentUser);
</script>
