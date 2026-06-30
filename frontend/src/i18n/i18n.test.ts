import { beforeEach, describe, expect, it } from 'vitest';

import { setLocale, t, useI18n } from './index';

describe('i18n', () => {
  beforeEach(() => {
    window.localStorage.clear();
    setLocale('en');
  });

  it('translates a message key in English and Chinese', () => {
    expect(t('nav.dashboard')).toBe('Dashboard');

    setLocale('zh-CN');

    expect(t('nav.dashboard')).toBe('仪表盘');
  });

  it('persists the selected locale', () => {
    setLocale('zh-CN');

    expect(window.localStorage.getItem('tradingagents.locale')).toBe('zh-CN');
    expect(useI18n().locale.value).toBe('zh-CN');
  });

  it('interpolates parameters', () => {
    expect(t('common.publicSnapshot', { ticker: 'NVDA' })).toBe('NVDA public snapshot');

    setLocale('zh-CN');

    expect(t('common.publicSnapshot', { ticker: 'NVDA' })).toBe('NVDA 公开快照');
  });
});
