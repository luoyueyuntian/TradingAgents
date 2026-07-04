import { beforeEach, describe, expect, it, vi } from 'vitest';

async function loadI18nModule() {
  vi.resetModules();
  return import('./index');
}

describe('i18n', () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it('defaults the UI locale to Chinese when no preference is stored', async () => {
    const { useI18n } = await loadI18nModule();

    expect(useI18n().locale.value).toBe('zh-CN');
  });

  it('uses the saved default UI locale when no explicit override exists', async () => {
    window.localStorage.setItem('tradingagents.defaultLocale', 'en');

    const { useI18n } = await loadI18nModule();

    expect(useI18n().locale.value).toBe('en');
  });

  it('translates a message key in English and Chinese', async () => {
    const { setLocale, t } = await loadI18nModule();

    setLocale('en');
    expect(t('nav.dashboard')).toBe('Dashboard');

    setLocale('zh-CN');
    expect(t('nav.dashboard')).toBe('仪表盘');
  });

  it('persists the selected locale override', async () => {
    const { setLocale, useI18n } = await loadI18nModule();

    setLocale('zh-CN');

    expect(window.localStorage.getItem('tradingagents.locale')).toBe('zh-CN');
    expect(useI18n().locale.value).toBe('zh-CN');
  });

  it('persists the default locale separately from the explicit override', async () => {
    const { setDefaultLocale, setLocale, useI18n } = await loadI18nModule();

    setLocale('en');
    setDefaultLocale('zh-CN');

    expect(window.localStorage.getItem('tradingagents.locale')).toBe('en');
    expect(window.localStorage.getItem('tradingagents.defaultLocale')).toBe('zh-CN');
    expect(useI18n().locale.value).toBe('en');
  });

  it('interpolates parameters', async () => {
    const { setLocale, t } = await loadI18nModule();

    setLocale('en');
    expect(t('common.publicSnapshot', { ticker: 'NVDA' })).toBe('NVDA public snapshot');

    setLocale('zh-CN');
    expect(t('common.publicSnapshot', { ticker: 'NVDA' })).toBe('NVDA 公开快照');
  });
});
