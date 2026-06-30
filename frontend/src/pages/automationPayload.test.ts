import { describe, expect, it } from 'vitest';

import { buildAutomationPayload, parseAutomationTickers } from './automationPayload';

describe('automation payload helpers', () => {
  it('normalizes manual ticker input', () => {
    expect(parseAutomationTickers(' nvda, msft\nNVDA  0700.HK ')).toEqual(['NVDA', 'MSFT', '0700.HK']);
  });

  it('builds the backend automation create payload shape', () => {
    const payload = buildAutomationPayload({
      name: ' Morning Sweep ',
      source: 'manual',
      cadence: 'weekly',
      weekday: 'fri',
      time: '09:30',
      tickers: 'nvda msft',
      enabled: true,
    });

    expect(payload).toEqual({
      name: 'Morning Sweep',
      source: 'manual',
      cadence: 'weekly',
      weekday: 'fri',
      time_of_day: '09:30',
      tickers: ['NVDA', 'MSFT'],
      enabled: true,
      analysis_config: {
        analysts: ['market', 'social', 'news', 'fundamentals'],
        llm_provider: 'openai',
        research_depth: 1,
        output_language: 'English',
      },
    });
    expect(payload).not.toHaveProperty('time');
  });

  it('omits weekday and manual tickers for daily watchlist rules', () => {
    const payload = buildAutomationPayload({
      name: 'Watchlist',
      source: 'watchlist',
      cadence: 'daily',
      weekday: 'fri',
      time: '08:45',
      tickers: 'nvda msft',
      enabled: false,
    });

    expect(payload.weekday).toBeNull();
    expect(payload.tickers).toEqual([]);
  });
});
