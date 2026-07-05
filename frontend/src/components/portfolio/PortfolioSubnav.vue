<template>
  <nav class="uno-mb-4 uno-flex uno-flex-wrap uno-gap-2" aria-label="Portfolio navigation">
    <RouterLink
      v-for="item in items"
      :key="item.to"
      :to="item.to"
      class="uno-rounded-full uno-border uno-border-[#dce7e7] uno-px-3 uno-py-1.5 uno-text-sm uno-font-700 uno-no-underline"
      :class="route.path === item.to ? 'uno-bg-[#14363a] uno-text-white' : 'uno-bg-white uno-text-[#35565a]'"
    >
      {{ item.label }}
    </RouterLink>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink, useRoute } from 'vue-router';

import { useI18n } from '../../i18n';

const route = useRoute();
const { t } = useI18n();

const items = computed(() => [
  { to: '/portfolio', label: t('nav.portfolio') },
  { to: '/portfolio/watchlist', label: t('common.watchlist') },
  { to: '/portfolio/positions', label: t('portfolio.positions') },
  { to: '/portfolio/stock-groups', label: t('portfolio.stockGroups') },
  { to: '/portfolio/alerts', label: t('portfolio.alerts') },
]);
</script>
