import { describe, expect, it } from 'vitest';

import {
  buildAnalysisRequestPayload,
  buildStockSearchPath,
  formatAnalysisDate,
  marketProfileForStockMarket,
  normalizeStockOptions,
  parseAnalysisDate,
} from './analyzeStockSelection';

describe('analyze stock selection helpers', () => {
  it('maps the selected stock market to the analysis market profile', () => {
    expect(marketProfileForStockMarket('us')).toBe('default');
    expect(marketProfileForStockMarket('hk')).toBe('default');
    expect(marketProfileForStockMarket('cn_a')).toBe('cn_a');
  });

  it('builds encoded stock search API paths', () => {
    expect(buildStockSearchPath('hk', '腾讯', 25)).toBe('/api/stocks?market=hk&q=%E8%85%BE%E8%AE%AF&limit=25');
    expect(buildStockSearchPath('us', '', 100)).toBe('/api/stocks?market=us&limit=100');
  });

  it('normalizes backend stock rows into select options', () => {
    expect(normalizeStockOptions([
      { market: 'us', symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' },
      { market: 'hk', symbol: '0700.HK', name: '腾讯控股', exchange: 'HKEX' },
    ])).toEqual([
      {
        market: 'us',
        symbol: 'AAPL',
        name: 'Apple Inc.',
        exchange: 'NASDAQ',
        label: 'AAPL · Apple Inc. · NASDAQ',
      },
      {
        market: 'hk',
        symbol: '0700.HK',
        name: '腾讯控股',
        exchange: 'HKEX',
        label: '0700.HK · 腾讯控股 · HKEX',
      },
    ]);
  });

  it('derives the request market profile from the selected market when no explicit override is set', () => {
    const payload = buildAnalysisRequestPayload({
      stock_market: 'cn_a',
      ticker: '600519.SS',
      company_name: '',
      date: '2026-06-30',
      analysts: ['market'],
      llm_provider: 'openai',
      quick_think_model: 'quick-model',
      deep_think_model: 'deep-model',
      research_depth: 3,
      output_language: 'Chinese',
      market_profile: '',
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

    expect(payload.market_profile).toBe('cn_a');
    expect(payload.ticker).toBe('600519.SS');
    expect(payload.max_risk_discuss_rounds).toBe(2);
    expect(payload.max_recur_limit).toBe(150);
    expect(payload.checkpoint_enabled).toBe(true);
    expect(payload.benchmark_ticker).toBe('QQQ');
    expect(payload.backend_url).toBe('https://example.invalid/v1');
    expect(payload.temperature).toBe(0.2);
    expect(payload.google_thinking_level).toBe('high');
    expect(payload.openai_reasoning_effort).toBe('medium');
    expect(payload.anthropic_effort).toBe('low');
  });

  it('prefers the explicit form market profile and omits cleared optional numeric overrides', () => {
    const payload = buildAnalysisRequestPayload({
      stock_market: 'us',
      ticker: 'NVDA',
      company_name: '',
      date: '2026-06-30',
      analysts: ['market'],
      llm_provider: 'openai',
      quick_think_model: 'quick-model',
      deep_think_model: 'deep-model',
      research_depth: 3,
      output_language: 'English',
      market_profile: 'cn_a',
      max_risk_discuss_rounds: '',
      max_recur_limit: '',
      checkpoint_enabled: false,
      benchmark_ticker: '',
      backend_url: '',
      temperature: '',
      google_thinking_level: '',
      openai_reasoning_effort: '',
      anthropic_effort: '',
    });

    expect(payload.market_profile).toBe('cn_a');
    expect(payload.max_risk_discuss_rounds).toBeNull();
    expect(payload.max_recur_limit).toBeNull();
    expect(payload.temperature).toBeNull();
  });

  it('includes company_name when the selected stock provides one', () => {
    const payload = buildAnalysisRequestPayload({
      stock_market: 'us',
      ticker: 'AAPL',
      company_name: 'Apple Inc.',
      date: '2026-06-30',
      analysts: ['market'],
      llm_provider: 'openai',
      quick_think_model: 'quick-model',
      deep_think_model: 'deep-model',
      research_depth: 3,
      output_language: 'English',
      market_profile: 'default',
      max_risk_discuss_rounds: '',
      max_recur_limit: '',
      checkpoint_enabled: false,
      benchmark_ticker: '',
      backend_url: '',
      temperature: '',
      google_thinking_level: '',
      openai_reasoning_effort: '',
      anthropic_effort: '',
    });

    expect(payload.company_name).toBe('Apple Inc.');
  });

  it('round-trips date picker values as yyyy-mm-dd strings', () => {
    const parsed = parseAnalysisDate('2026-07-03');

    expect(parsed).toBeInstanceOf(Date);
    expect(formatAnalysisDate(parsed)).toBe('2026-07-03');
    expect(parseAnalysisDate('')).toBeNull();
    expect(formatAnalysisDate(null)).toBe('');
  });
});
