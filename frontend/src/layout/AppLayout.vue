<template>
  <div class="uno-grid uno-min-h-screen uno-min-w-[320px] uno-grid-cols-[260px_minmax(0,1fr)] uno-bg-[#f6f7f7] uno-font-sans uno-text-[15px] uno-text-[#162326] max-[900px]:uno-grid-cols-1">
    <aside class="app-sidebar">
      <RouterLink class="uno-flex uno-items-center uno-gap-3 uno-px-[0.55rem] uno-pb-4 uno-pt-[0.65rem] uno-text-inherit uno-no-underline" to="/">
        <span class="uno-grid uno-h-[42px] uno-w-[42px] uno-place-items-center uno-rounded-lg uno-bg-[#f4b740] uno-font-800 uno-text-[#2b2107]">TA</span>
        <span>
          <strong>TradingAgents</strong>
          <small class="uno-block uno-text-[#b8c8c8]">{{ t('brand.subtitle') }}</small>
        </span>
      </RouterLink>

      <nav class="sidebar-navigation" :aria-label="t('topbar.primaryNavigation')">
        <section
          v-for="section in visibleNavigationSections"
          :key="section.id"
          class="sidebar-section"
          :aria-labelledby="`nav-section-${section.id}`"
        >
          <h2 :id="`nav-section-${section.id}`" class="sidebar-heading">{{ t(section.labelKey) }}</h2>
          <ul class="sidebar-links">
            <li v-for="item in section.items" :key="item.path">
              <RouterLink v-slot="{ href, navigate }" :to="item.path" custom>
                <a
                  :href="href"
                  class="sidebar-link"
                  :class="{ 'sidebar-link-active': isNavigationActive(item.path) }"
                  :aria-current="isNavigationActive(item.path) ? 'page' : undefined"
                  :title="t(item.descriptionKey)"
                  @click="navigate"
                >
                  <i :class="item.icon" aria-hidden="true" />
                  <span>{{ t(item.labelKey) }}</span>
                </a>
              </RouterLink>
            </li>
          </ul>
        </section>
      </nav>
    </aside>

    <div class="uno-min-w-0">
      <header class="uno-sticky uno-top-0 uno-z-10 uno-flex uno-min-h-[64px] uno-items-center uno-justify-between uno-gap-4 uno-border-b uno-border-[#dce7e7] uno-bg-white/90 uno-px-5 uno-py-3 uno-backdrop-blur-md max-[900px]:uno-flex-col max-[900px]:uno-items-stretch">
        <div data-testid="header-start" class="uno-min-w-0">
          <label class="uno-flex uno-items-center uno-gap-2 uno-text-sm">
            <span>{{ t('topbar.currentTenant') }}</span>
            <select
              v-if="session.state.tenants?.length"
              data-testid="tenant-switcher"
              :aria-label="t('topbar.switchTenant')"
              :value="session.state.currentUser?.tenant_id || ''"
              :disabled="switchingTenant"
              class="uno-max-w-[260px] uno-rounded-md uno-border uno-border-[#dce7e7] uno-bg-white uno-px-3 uno-py-2"
              @change="handleTenantChange"
            >
              <option v-if="!session.state.currentUser?.tenant_id" value="" disabled>{{ t('topbar.chooseTenant') }}</option>
              <option v-for="tenant in session.state.tenants" :key="tenant.tenant_id" :value="tenant.tenant_id">{{ tenant.display_name }}</option>
            </select>
            <span v-else>{{ t('topbar.noTenant') }}</span>
          </label>
          <p v-if="tenantSwitchError" role="alert" class="uno-m-0 uno-mt-1 uno-text-sm uno-text-red-700">{{ tenantSwitchError }}</p>
        </div>
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
              class="uno-absolute uno-right-0 uno-top-full uno-z-20 uno-min-w-[200px] uno-max-w-[280px] uno-rounded-lg uno-border uno-border-[#dce7e7] uno-bg-white uno-py-1 uno-shadow-lg"
            >
              <div class="uno-min-w-0 uno-border-b uno-border-[#e8eeee] uno-px-3 uno-py-2">
                <div class="uno-flex uno-items-center uno-gap-2 uno-text-[13px] uno-leading-5">
                  <strong class="uno-min-w-0 uno-flex-1 uno-truncate uno-text-[#132a2d]">{{ currentUserName }}</strong>
                  <span class="uno-shrink-0 uno-text-xs uno-text-[#6f8183]">{{ t(roleLabelKey) }}</span>
                </div>
                <p class="uno-m-0 uno-truncate uno-text-xs uno-leading-5 uno-text-[#6f8183]">
                  {{ t('topbar.tenantValue', { tenant: session.state.currentUser?.tenant_id || t('common.notSet') }) }}
                </p>
              </div>
              <nav class="uno-py-1" :aria-label="t('profile.title')">
                <RouterLink
                  to="/profile"
                  class="uno-flex uno-min-h-[32px] uno-items-center uno-gap-2 uno-px-3 uno-py-1 uno-text-[13px] uno-text-[#243a3d] uno-no-underline hover:uno-bg-[#f1f5f5] focus-visible:uno-bg-[#f1f5f5]"
                  @click="userMenuOpen = false"
                >
                  <i class="pi pi-user uno-text-sm" aria-hidden="true" />
                  <span>{{ t('profile.title') }}</span>
                </RouterLink>
                <button
                  type="button"
                  class="uno-flex uno-min-h-[32px] uno-w-full uno-cursor-pointer uno-items-center uno-gap-2 uno-border-0 uno-bg-transparent uno-px-3 uno-py-1 uno-text-left uno-font-inherit uno-text-[13px] uno-text-[#243a3d] hover:uno-bg-[#f1f5f5] focus-visible:uno-bg-[#f1f5f5]"
                  @click="handleLogout"
                >
                  <i class="pi pi-sign-out uno-text-sm" aria-hidden="true" />
                  <span>{{ t('auth.logout') }}</span>
                </button>
              </nav>
            </div>
          </div>
        </div>
      </header>

      <main class="uno-w-full uno-p-5">
        <div v-if="session.state.currentUser && !session.state.currentUser.tenant_id && route.path !== '/profile'" role="status" class="uno-rounded-lg uno-bg-white uno-p-6">
          {{ t('topbar.noTenantHelp') }}
        </div>
        <RouterView v-else />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import Button from 'primevue/button';
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router';

import { setDefaultLocale, useI18n, type Locale } from '../i18n';
import { navigationGroups, navigationSections } from '../router/pages';
import { apiGet } from '../services/api';
import { useSession } from '../stores/session';
import type { JsonRecord } from '../utils/format';

const router = useRouter();
const route = useRoute();
const session = useSession();
const { locale, locales, t } = useI18n();
const languageMenuOpen = ref(false);
const languageMenuRef = ref<HTMLElement | null>(null);
const userMenuOpen = ref(false);
const switchingTenant = ref(false);
const tenantSwitchError = ref('');

async function handleTenantChange(event: Event) {
  const select = event.target as HTMLSelectElement;
  const tenantId = select.value;
  const previous = session.state.currentUser?.tenant_id || '';
  if (tenantId === previous) return;
  switchingTenant.value = true;
  tenantSwitchError.value = '';
  try {
    await session.switchTenant(tenantId);
    // A fresh document tears down tenant-scoped stores, subscriptions and in-flight callbacks.
    window.location.assign('/');
  } catch (error) {
    tenantSwitchError.value = error instanceof Error ? error.message : String(error);
    select.value = previous;
    switchingTenant.value = false;
  }
}


const visibleNavigationSections = computed(() => navigationSections.map((section) => ({
  ...section,
  items: navigationGroups.filter((item) => item.section === section.id && (
    item.minRole !== 'admin' || session.isAdmin.value
  )),
})).filter((section) => section.items.length > 0));

function isNavigationActive(path: string) {
  return route.path === path || (path !== '/' && route.path.startsWith(`${path}/`));
}

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

watch(() => session.state.tenantId, (value) => {
  if (value) {
    void loadDefaultUiLanguage();
  }
});

onMounted(() => {
  document.addEventListener('click', handleDocumentClick);
  void loadDefaultUiLanguage();
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick);
});
</script>

<style scoped>
.app-sidebar {
  position: sticky;
  top: 0;
  display: flex;
  flex-direction: column;
  height: 100dvh;
  min-height: 0;
  padding: 16px;
  border-right: 1px solid #2d4144;
  background: #162326;
  color: #f7fbfb;
}

.sidebar-navigation {
  min-height: 0;
  overflow-y: auto;
  margin-top: 16px;
  padding: 4px;
  scrollbar-width: thin;
  scrollbar-color: #4e6669 transparent;
}

.sidebar-section + .sidebar-section {
  margin-top: 22px;
  padding-top: 20px;
  border-top: 1px solid #304346;
}

.sidebar-heading {
  margin: 0 0 10px;
  padding: 0 12px;
  color: #a3b9bc;
  font-size: 12px;
  font-weight: 600;
  line-height: 20px;
  letter-spacing: 0.04em;
}

.sidebar-links {
  display: grid;
  gap: 4px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.sidebar-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 44px;
  padding: 10px 12px;
  border-radius: 8px;
  color: #d0dfe1;
  line-height: 24px;
  text-decoration: none;
  transition: background-color 150ms ease, color 150ms ease;
}

.sidebar-link > i {
  flex: 0 0 20px;
  font-size: 17px;
  text-align: center;
  color: #a3b9bc;
}

.sidebar-link:hover {
  background: #22373b;
  color: #fff;
}

.sidebar-link:focus-visible {
  outline: 2px solid #f4b740;
  outline-offset: 2px;
}

.sidebar-link-active,
.sidebar-link-active:hover {
  background: #334039;
  color: #ffda83;
  font-weight: 600;
}

.sidebar-link-active > i {
  color: inherit;
}

.sidebar-link-active::before {
  position: absolute;
  top: 12px;
  bottom: 12px;
  left: 0;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: #f4b740;
  content: '';
}

@media (max-width: 900px) {
  .app-sidebar {
    position: static;
    height: auto;
  }

  .sidebar-navigation {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
    gap: 20px;
    margin-top: 8px;
  }

  .sidebar-section + .sidebar-section {
    margin-top: 0;
    padding-top: 0;
    border-top: 0;
  }
}

@media (max-width: 480px) {
  .sidebar-links {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-link {
    transition: none;
  }
}
</style>
