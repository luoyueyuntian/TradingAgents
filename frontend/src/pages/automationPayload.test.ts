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
      llm_provider: 'google',
      quick_think_model: 'gemini-3.5-flash',
      deep_think_model: 'gemini-3.1-pro-preview',
      research_depth: 3,
      output_language: 'Chinese',
      market_profile: 'cn_a',
      max_risk_discuss_rounds: 2,
      max_recur_limit: 150,
      checkpoint_enabled: true,
      benchmark_ticker: 'QQQ',
      backend_url: 'https://example.invalid/v1',
      temperature: 0.2,
      google_thinking_level: 'high',
      openai_reasoning_effort: 'medium',
      anthropic_effort: 'low',
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
        llm_provider: 'google',
        quick_think_model: 'gemini-3.5-flash',
        deep_think_model: 'gemini-3.1-pro-preview',
        research_depth: 3,
        output_language: 'Chinese',
        market_profile: 'cn_a',
        max_risk_discuss_rounds: 2,
        max_recur_limit: 150,
        checkpoint_enabled: true,
        benchmark_ticker: 'QQQ',
        backend_url: 'https://example.invalid/v1',
        temperature: 0.2,
        google_thinking_level: 'high',
        openai_reasoning_effort: 'medium',
        anthropic_effort: 'low',
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
      llm_provider: 'openai',
      quick_think_model: '',
      deep_think_model: '',
      research_depth: 1,
      output_language: 'English',
      market_profile: 'default',
      max_risk_discuss_rounds: 1,
      max_recur_limit: 100,
      checkpoint_enabled: false,
      benchmark_ticker: '',
      backend_url: '',
      temperature: null,
      google_thinking_level: '',
      openai_reasoning_effort: '',
      anthropic_effort: '',
    });

    expect(payload.weekday).toBeNull();
    expect(payload.tickers).toEqual([]);
  });
});
