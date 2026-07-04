import { computed, ref } from 'vue';

import { messages, type Locale, type MessageKey } from './messages';

export type { Locale, MessageKey };

type MessageParams = Record<string, string | number>;

const STORAGE_KEY = 'tradingagents.locale';
const DEFAULT_STORAGE_KEY = 'tradingagents.defaultLocale';

export const locales: Array<{ label: string; value: Locale }> = [
  { label: 'English', value: 'en' },
  { label: '中文', value: 'zh-CN' },
];

function isLocale(value: string | null): value is Locale {
  return value === 'en' || value === 'zh-CN';
}

function readStoredLocale(key: string): Locale | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const stored = window.localStorage.getItem(key);
  return isLocale(stored) ? stored : null;
}

function readInitialLocale(): Locale {
  return readStoredLocale(STORAGE_KEY) || readStoredLocale(DEFAULT_STORAGE_KEY) || 'zh-CN';
}

const currentLocale = ref<Locale>(readInitialLocale());

export function setLocale(locale: Locale) {
  currentLocale.value = locale;
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(STORAGE_KEY, locale);
  }
}

export function setDefaultLocale(locale: Locale) {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(DEFAULT_STORAGE_KEY, locale);
  }
  if (!readStoredLocale(STORAGE_KEY)) {
    currentLocale.value = locale;
  }
}

export function t(key: MessageKey, params: MessageParams = {}): string {
  const template = messages[currentLocale.value][key] || messages.en[key] || key;
  return template.replace(/\{(\w+)\}/g, (_, name: string) => {
    const value = params[name];
    return value === undefined ? `{${name}}` : String(value);
  });
}

export function useI18n() {
  return {
    locale: computed({
      get: () => currentLocale.value,
      set: setLocale,
    }),
    locales,
    setLocale,
    t,
  };
}
