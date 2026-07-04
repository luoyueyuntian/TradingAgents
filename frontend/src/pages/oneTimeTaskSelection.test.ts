import { describe, expect, it } from 'vitest';

import { mergeResolvedTickers, upsertManualStock } from './oneTimeTaskSelection';

describe('one-time task selection helpers', () => {
  it('keeps previously selected stocks when switching markets and dedupes merged sources', () => {
    const manual = upsertManualStock([], {
      market: 'cn_a',
      symbol: '600519.SH',
      name: '贵州茅台',
      exchange: 'SSE',
    });
    const withUs = upsertManualStock(manual, {
      market: 'us',
      symbol: 'AAPL',
      name: 'Apple Inc.',
      exchange: 'NASDAQ',
    });

    expect(withUs.map((item) => item.symbol)).toEqual(['600519.SH', 'AAPL']);

    const resolved = mergeResolvedTickers({
      manualStocks: withUs,
      selectedGroups: [{ id: 'group-1', name: 'AI Leaders', tickers: ['AAPL', 'NVDA'] }],
      includeWatchlist: true,
      watchlistTickers: ['NVDA', 'MSFT'],
    });

    expect(resolved).toEqual(['600519.SH', 'AAPL', 'NVDA', 'MSFT']);
  });
});
