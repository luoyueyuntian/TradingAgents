<template>
  <div class="uno-grid uno-min-h-screen uno-min-w-[320px] uno-grid-cols-[260px_minmax(0,1fr)] uno-bg-[#f6f7f7] uno-font-sans uno-text-[15px] uno-text-[#162326] max-[900px]:uno-grid-cols-1">
    <aside class="uno-sticky uno-top-0 uno-h-screen uno-border-r uno-border-[#dbe5e5] uno-bg-[#162326] uno-p-4 uno-text-[#f7fbfb] max-[900px]:uno-static max-[900px]:uno-h-auto">
      <RouterLink class="uno-flex uno-items-center uno-gap-3 uno-px-[0.55rem] uno-pb-4 uno-pt-[0.65rem] uno-text-inherit uno-no-underline" to="/">
        <span class="uno-grid uno-h-[42px] uno-w-[42px] uno-place-items-center uno-rounded-lg uno-bg-[#f4b740] uno-font-800 uno-text-[#2b2107]">TA</span>
        <span>
          <strong>TradingAgents</strong>
          <small class="uno-block uno-text-[#b8c8c8]">{{ t('brand.subtitle') }}</small>
        </span>
      </RouterLink>

      <nav class="uno-mt-2 uno-grid uno-gap-1 max-[900px]:uno-grid-cols-[repeat(auto-fit,minmax(130px,1fr))]" :aria-label="t('topbar.primaryNavigation')">
        <RouterLink
          v-for="item in navigationGroups"
          :key="item.path"
          :to="item.path"
          class="uno-flex uno-min-h-[42px] uno-items-center uno-gap-[0.65rem] uno-rounded-lg uno-px-[0.7rem] uno-py-[0.55rem] uno-text-[#dce8e8] uno-no-underline"
          active-class="uno-bg-[#e8f0ff] uno-text-[#18233f]"
          :title="t(item.descriptionKey)"
        >
          <i :class="item.icon" />
          <span>{{ t(item.labelKey) }}</span>
        </RouterLink>
      </nav>
    </aside>

    <div class="uno-min-w-0">
      <header class="uno-sticky uno-top-0 uno-z-10 uno-flex uno-min-h-[64px] uno-items-center uno-justify-between uno-gap-4 uno-border-b uno-border-[#dce7e7] uno-bg-white/90 uno-px-5 uno-py-3 uno-backdrop-blur-md max-[900px]:uno-flex-col max-[900px]:uno-items-start">
        <div class="uno-flex uno-flex-wrap uno-items-center uno-gap-2">
          <span class="uno-text-[#6f8183]">{{ t('topbar.tenant') }}</span>
          <InputText
            v-model="tenantDraft"
            class="uno-w-[180px] max-[900px]:uno-w-[min(100%,240px)]"
            :placeholder="t('common.default')"
            @change="session.setTenantId(tenantDraft)"
          />
          <span class="uno-text-[#6f8183]">{{ t('topbar.apiToken') }}</span>
          <InputText
            v-model="tokenDraft"
            class="uno-w-[180px] max-[900px]:uno-w-[min(100%,240px)]"
            type="password"
            :placeholder="t('common.optional')"
            @change="session.setApiToken(tokenDraft)"
          />
          <span class="uno-text-[#6f8183]">{{ t('topbar.language') }}</span>
          <Select
            v-model="locale"
            class="uno-w-[180px] max-[900px]:uno-w-[min(100%,240px)]"
            :options="locales"
            option-label="label"
            option-value="value"
            :aria-label="t('topbar.language')"
          />
        </div>
        <div class="uno-flex uno-items-center uno-gap-[0.35rem] max-[900px]:uno-w-full max-[900px]:uno-justify-end">
          <Button icon="pi pi-search" text rounded :aria-label="t('topbar.workspaceSearch')" @click="router.push('/workspace')" />
        </div>
      </header>

      <main class="uno-w-full uno-p-5">
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
