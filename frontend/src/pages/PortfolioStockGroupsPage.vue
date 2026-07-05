<template>
  <section>
    <PageHeader
      :eyebrow="t('portfolio.eyebrow')"
      :title="t('portfolio.stockGroups')"
      :description="t('nav.portfolioDesc')"
    />
    <PortfolioSubnav />
  </section>
</template>

<script setup lang="ts">
import PageHeader from '../components/PageHeader.vue';
import PortfolioSubnav from '../components/portfolio/PortfolioSubnav.vue';
import { useI18n } from '../i18n';

const { t } = useI18n();
</script>
