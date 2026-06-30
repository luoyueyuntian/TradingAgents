<template>
  <div class="app-shell">
    <aside class="side-nav">
      <RouterLink class="brand" to="/">
        <span class="brand-mark">TA</span>
        <span>
          <strong>TradingAgents</strong>
          <small>{{ t('brand.subtitle') }}</small>
        </span>
      </RouterLink>

      <nav class="nav-list" :aria-label="t('topbar.primaryNavigation')">
        <RouterLink
          v-for="item in navigationGroups"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :title="t(item.descriptionKey)"
        >
          <i :class="item.icon" />
          <span>{{ t(item.labelKey) }}</span>
        </RouterLink>
      </nav>
    </aside>

    <div class="app-main">
      <header class="topbar">
        <div class="runtime-fields">
          <span class="field-label">{{ t('topbar.tenant') }}</span>
          <InputText
            v-model="tenantDraft"
            class="topbar-input"
            :placeholder="t('common.default')"
            @change="session.setTenantId(tenantDraft)"
          />
          <span class="field-label">{{ t('topbar.apiToken') }}</span>
          <InputText
            v-model="tokenDraft"
            class="topbar-input"
            type="password"
            :placeholder="t('common.optional')"
            @change="session.setApiToken(tokenDraft)"
          />
          <span class="field-label">{{ t('topbar.language') }}</span>
          <Select
            v-model="locale"
            class="topbar-input"
            :options="locales"
            option-label="label"
            option-value="value"
            :aria-label="t('topbar.language')"
          />
        </div>
        <div class="topbar-actions">
          <Button icon="pi pi-search" text rounded :aria-label="t('topbar.workspaceSearch')" @click="router.push('/workspace')" />
        </div>
      </header>

      <main class="page-surface">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import InputText from 'primevue/inputtext';
import Select from 'primevue/select';
import { ref } from 'vue';
import { RouterLink, RouterView, useRouter } from 'vue-router';

import { useI18n } from '../i18n';
import { navigationGroups } from '../router/pages';
import { useSession } from '../stores/session';

const router = useRouter();
const session = useSession();
const { locale, locales, t } = useI18n();
const tenantDraft = ref(session.state.tenantId);
const tokenDraft = ref(session.state.apiToken);
</script>
