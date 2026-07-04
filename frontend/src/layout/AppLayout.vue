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
          active-class="uno-text-[#0099ff]"
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
          <div ref="languageMenuRef" data-testid="language-menu" class="uno-relative">
            <button
              data-testid="language-trigger"
              type="button"
              class="uno-inline-flex uno-min-h-10 uno-cursor-pointer uno-items-center uno-gap-1.5 uno-border-0 uno-bg-transparent uno-p-0 uno-text-[#243a3d] hover:uno-text-[#132a2d]"
              :aria-expanded="languageMenuOpen"
              :aria-label="t('topbar.language')"
              @click="languageMenuOpen = !languageMenuOpen"
            >
              <span>{{ currentLocaleLabel }}</span>
              <i :class="languageMenuOpen ? 'pi pi-angle-up uno-text-xs' : 'pi pi-angle-down uno-text-xs'" />
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
            data-testid="current-member-menu"
            class="uno-relative"
            @focusout="handleCurrentMemberMenuFocusOut"
          >
            <button
              data-testid="current-member-trigger"
              type="button"
              class="uno-inline-flex uno-min-h-10 uno-max-w-[220px] uno-cursor-pointer uno-items-center uno-gap-1.5 uno-border-0 uno-bg-transparent uno-p-0 uno-text-[#243a3d] hover:uno-text-[#132a2d] max-[900px]:uno-max-w-full"
              :aria-expanded="currentMemberMenuOpen"
              :aria-label="t('topbar.currentMember')"
              @click="toggleCurrentMemberMenu"
            >
              <span class="uno-max-w-[190px] uno-truncate">{{ currentMemberLabel }}</span>
              <i :class="currentMemberMenuOpen ? 'pi pi-angle-up uno-text-xs' : 'pi pi-angle-down uno-text-xs'" />
            </button>
            <div
              v-if="currentMemberMenuOpen"
              class="uno-absolute uno-right-0 uno-top-[calc(100%+0.35rem)] uno-z-20 uno-grid uno-min-w-[190px] uno-gap-1 uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-2 uno-shadow-lg"
            >
              <button
                v-for="option in memberOptions"
                :key="option.value"
                :data-testid="`current-member-option-${option.value}`"
                type="button"
                class="uno-flex uno-min-h-9 uno-cursor-pointer uno-items-center uno-justify-between uno-gap-3 uno-rounded-md uno-border-0 uno-bg-transparent uno-px-2 uno-py-1.5 uno-text-left uno-text-[#243a3d] hover:uno-bg-[#f1f6f6]"
                @click="selectCurrentMember(option.value)"
              >
                <span class="uno-truncate">{{ option.label }}</span>
                <i v-if="option.value === currentMemberDraft" class="pi pi-check uno-text-[#1c7f5f]" />
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
              data-testid="user-menu-trigger"
              type="button"
              class="uno-inline-flex uno-min-h-10 uno-cursor-pointer uno-items-center uno-gap-1.5 uno-border-0 uno-bg-transparent uno-p-0 uno-text-[#243a3d] hover:uno-text-[#132a2d]"
              :aria-expanded="userMenuOpen"
            >
              <strong class="uno-max-w-[180px] uno-truncate">{{ currentUserName }}</strong>
              <i :class="userMenuOpen ? 'pi pi-angle-up uno-text-xs' : 'pi pi-angle-down uno-text-xs'" />
            </button>
            <div
              v-if="userMenuOpen"
              class="uno-absolute uno-right-0 uno-top-full uno-z-20 uno-grid uno-min-w-[240px] uno-gap-2 uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-p-3 uno-shadow-lg"
            >
              <div class="uno-min-w-0">
                <strong class="uno-block uno-truncate uno-text-[#132a2d]">{{ currentUserName }}</strong>
                <small class="uno-block uno-truncate uno-text-[#6f8183]">
                  {{ t(roleLabelKey) }}
                </small>
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
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { RouterLink, RouterView, useRouter } from 'vue-router';

import { setDefaultLocale, useI18n, type Locale } from '../i18n';
import { navigationGroups } from '../router/pages';
import { apiGet } from '../services/api';
import { useSession } from '../stores/session';
import type { JsonRecord } from '../utils/format';

const router = useRouter();
const session = useSession();
const { locale, locales, t } = useI18n();
const languageMenuOpen = ref(false);
const languageMenuRef = ref<HTMLElement | null>(null);
const currentMemberMenuOpen = ref(false);
const userMenuOpen = ref(false);
const currentMemberDraft = ref(session.state.currentMemberId);
const members = ref<JsonRecord[]>([]);

const visibleNavigationGroups = computed(() => navigationGroups.filter((item) => (
  item.minRole !== 'admin' || session.isAdmin.value
)));
const memberOptions = computed(() => members.value.map((member) => ({
  label: String(member.name || member.id || ''),
  value: String(member.id || ''),
})));
const currentMemberLabel = computed(() => (
  memberOptions.value.find((member) => member.value === currentMemberDraft.value)?.label || t('topbar.memberPlaceholder')
));

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

function handleDocumentClick(event: MouseEvent) {
  const target = event.target;
  if (
    languageMenuOpen.value
    && languageMenuRef.value
    && target instanceof Node
    && !languageMenuRef.value.contains(target)
  ) {
    languageMenuOpen.value = false;
  }
}

function handleUserMenuFocusOut(event: FocusEvent) {
  const nextTarget = event.relatedTarget;
  if (nextTarget instanceof Node && event.currentTarget instanceof HTMLElement && event.currentTarget.contains(nextTarget)) {
    return;
  }
  userMenuOpen.value = false;
}

function handleCurrentMemberMenuFocusOut(event: FocusEvent) {
  const nextTarget = event.relatedTarget;
  if (nextTarget instanceof Node && event.currentTarget instanceof HTMLElement && event.currentTarget.contains(nextTarget)) {
    return;
  }
  currentMemberMenuOpen.value = false;
}

function toggleCurrentMemberMenu() {
  currentMemberMenuOpen.value = !currentMemberMenuOpen.value;
}

function selectCurrentMember(value: string) {
  currentMemberDraft.value = value;
  session.setCurrentMemberId(value);
  currentMemberMenuOpen.value = false;
}

async function loadMembers() {
  try {
    members.value = await apiGet<JsonRecord[]>('/api/members', session.apiContext.value);
    if (currentMemberDraft.value && !members.value.some((member) => String(member.id) === currentMemberDraft.value)) {
      currentMemberDraft.value = '';
      session.setCurrentMemberId('');
    }
  } catch {
    members.value = [];
  }
}

async function loadDefaultUiLanguage() {
  try {
    const settings = await apiGet<JsonRecord>('/api/settings', session.apiContext.value);
    const configured = settings.workspace?.default_ui_language;
    if (configured === 'en' || configured === 'zh-CN') {
      setDefaultLocale(configured);
    }
  } catch {
    // Ignore settings fetch failures here so header controls still render.
  }
}

async function handleLogout() {
  await session.logout();
  await router.push('/login');
}

watch(() => session.state.tenantId, async (value) => {
  currentMemberDraft.value = session.state.currentMemberId;
  if (value) {
    await Promise.all([loadMembers(), loadDefaultUiLanguage()]);
    return;
  }
  members.value = [];
});

watch(() => session.state.currentMemberId, (value) => {
  currentMemberDraft.value = value;
});

onMounted(() => {
  document.addEventListener('click', handleDocumentClick);
  void Promise.all([loadMembers(), loadDefaultUiLanguage()]);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick);
});
</script>
