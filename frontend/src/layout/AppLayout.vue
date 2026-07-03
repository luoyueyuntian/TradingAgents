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
          v-for="item in visibleNavigationGroups"
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
      <header class="uno-sticky uno-top-0 uno-z-10 uno-flex uno-min-h-[64px] uno-items-center uno-justify-between uno-gap-4 uno-border-b uno-border-[#dce7e7] uno-bg-white/90 uno-px-5 uno-py-3 uno-backdrop-blur-md max-[900px]:uno-flex-col max-[900px]:uno-items-stretch">
        <div data-testid="header-start" class="uno-min-w-0" />
        <div data-testid="header-actions" class="uno-flex uno-flex-wrap uno-items-center uno-justify-end uno-gap-[0.55rem] max-[900px]:uno-w-full">
          <Button icon="pi pi-search" text rounded :aria-label="t('topbar.workspaceSearch')" @click="router.push('/workspace')" />
          <div data-testid="language-menu" class="uno-relative">
            <button
              data-testid="language-trigger"
              type="button"
              class="uno-flex uno-min-h-10 uno-cursor-pointer uno-items-center uno-gap-2 uno-rounded-lg uno-border uno-border-[#d5e2e2] uno-bg-white uno-px-3 uno-py-2 uno-text-[#243a3d] hover:uno-border-[#90a9aa]"
              :aria-expanded="languageMenuOpen"
              :aria-label="t('topbar.language')"
              @click="languageMenuOpen = !languageMenuOpen"
            >
              <i class="pi pi-globe" />
              <span>{{ currentLocaleLabel }}</span>
              <i class="pi pi-angle-down uno-text-xs" />
            </button>
            <div
              v-if="languageMenuOpen"
              class="uno-absolute uno-right-0 uno-top-[calc(100%+0.35rem)] uno-z-20 uno-grid uno-min-w-[150px] uno-gap-1 uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-2 uno-shadow-lg"
            >
              <button
                v-for="option in locales"
                :key="option.value"
                type="button"
                class="uno-flex uno-min-h-9 uno-cursor-pointer uno-items-center uno-justify-between uno-gap-3 uno-rounded-md uno-border-0 uno-bg-transparent uno-px-2 uno-py-1.5 uno-text-left uno-text-[#243a3d] hover:uno-bg-[#f1f6f6]"
                :data-testid="`language-option-${option.value}`"
                @click="changeLocale(option.value)"
              >
                <span>{{ option.label }}</span>
                <i v-if="option.value === locale" class="pi pi-check uno-text-[#1c7f5f]" />
              </button>
            </div>
          </div>
          <div
            data-testid="user-menu"
            class="uno-relative"
            @mouseenter="userMenuOpen = true"
            @mouseleave="userMenuOpen = false"
            @focusin="userMenuOpen = true"
            @focusout="handleUserMenuFocusOut"
          >
            <button
              type="button"
              class="uno-flex uno-min-h-10 uno-cursor-pointer uno-items-center uno-gap-2 uno-rounded-lg uno-border uno-border-[#d5e2e2] uno-bg-[#162326] uno-px-3 uno-py-2 uno-text-white hover:uno-bg-[#223639]"
              :aria-expanded="userMenuOpen"
            >
              <strong class="uno-max-w-[180px] uno-truncate">{{ currentUserName }}</strong>
              <span class="uno-rounded-md uno-bg-white/12 uno-px-2 uno-py-0.5 uno-text-xs">{{ t(roleLabelKey) }}</span>
              <i class="pi pi-angle-down uno-text-xs" />
            </button>
            <div
              v-if="userMenuOpen"
              class="uno-absolute uno-right-0 uno-top-full uno-z-20 uno-grid uno-min-w-[240px] uno-gap-2 uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3 uno-shadow-lg"
            >
              <div class="uno-min-w-0">
                <strong class="uno-block uno-truncate uno-text-[#132a2d]">{{ currentUserName }}</strong>
                <small class="uno-block uno-truncate uno-text-[#6f8183]">
                  {{ t('topbar.tenantValue', { tenant: session.state.currentUser?.tenant_id || t('common.notSet') }) }}
                </small>
              </div>
              <Button icon="pi pi-sign-out" :label="t('auth.logout')" severity="secondary" class="uno-w-full" @click="handleLogout" />
            </div>
          </div>
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
import { computed, ref } from 'vue';
import { RouterLink, RouterView, useRouter } from 'vue-router';

import { useI18n, type Locale } from '../i18n';
import { navigationGroups } from '../router/pages';
import { useSession } from '../stores/session';

const router = useRouter();
const session = useSession();
const { locale, locales, t } = useI18n();
const languageMenuOpen = ref(false);
const userMenuOpen = ref(false);

const visibleNavigationGroups = computed(() => navigationGroups.filter((item) => (
  item.minRole !== 'admin' || session.isAdmin.value
)));

const roleLabelKey = computed(() => {
  const role = session.state.currentUser?.role;
  if (role === 'admin') {
    return 'auth.roleAdmin';
  }
  if (role === 'analyst') {
    return 'auth.roleAnalyst';
  }
  return 'auth.roleViewer';
});

const currentUserName = computed(() => (
  session.state.currentUser?.display_name || session.state.currentUser?.username || t('common.notSet')
));
const currentLocaleLabel = computed(() => (
  locales.find((item) => item.value === locale.value)?.label || locale.value
));

function changeLocale(value: Locale) {
  locale.value = value;
  languageMenuOpen.value = false;
}

function handleUserMenuFocusOut(event: FocusEvent) {
  const nextTarget = event.relatedTarget;
  if (nextTarget instanceof Node && event.currentTarget instanceof HTMLElement && event.currentTarget.contains(nextTarget)) {
    return;
  }
  userMenuOpen.value = false;
}

async function handleLogout() {
  await session.logout();
  await router.push('/login');
}
</script>
