import { describe, expect, it } from 'vitest';

import { buildOneTimeTaskPayload } from './oneTimeTaskPayload';

describe('one-time task payload helpers', () => {
  it('builds the backend payload with manual stocks, groups, watchlist, and analysis config', () => {
    const payload = buildOneTimeTaskPayload({
      name: ' Night basket ',
      scheduledFor: '2026-07-10 21:30',
      analysisDate: '2026-07-11',
      manualStocks: [{ market: 'us', symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' }],
      selectedGroupIds: ['group-1', 'group-2'],
      includeWatchlist: true,
      analysts: ['market', 'news'],
      llm_provider: 'openai',
      quick_think_model: 'gpt-5.4-mini',
      deep_think_model: 'gpt-5.5',
      research_depth: 3,
      output_language: 'Chinese',
      market_profile: 'default',
      max_risk_discuss_rounds: 2,
      max_recur_limit: 100,
      checkpoint_enabled: true,
      benchmark_ticker: 'QQQ',
      backend_url: '',
      temperature: '',
      google_thinking_level: '',
      openai_reasoning_effort: '',
      anthropic_effort: '',
    });

    expect(payload).toEqual({
      name: 'Night basket',
      scheduled_for: '2026-07-10 21:30',
      analysis_date: '2026-07-11',
      manual_stocks: [{ market: 'us', symbol: 'AAPL', name: 'Apple Inc.', exchange: 'NASDAQ' }],
      group_ids: ['group-1', 'group-2'],
      include_watchlist: true,
      analysis_config: expect.objectContaining({
        analysts: ['market', 'news'],
        llm_provider: 'openai',
        quick_think_model: 'gpt-5.4-mini',
        deep_think_model: 'gpt-5.5',
        research_depth: 3,
        output_language: 'Chinese',
      }),
    });
  });
});
