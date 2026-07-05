import { describe, expect, it } from 'vitest';

import {
  buildTickerHistoryPath,
  isWithinRecentLocalAnalysisWindow,
} from './tickerHistory';

describe('ticker history helpers', () => {
  it('builds the ticker history path with uppercase ticker and paging params', () => {
    expect(buildTickerHistoryPath({ ticker: 'aapl', assetType: 'stock', page: 2, pageSize: 10 }))
      .toBe('/api/runs/ticker-history?ticker=AAPL&asset_type=stock&page=2&page_size=10');
  });

  it('treats today yesterday and the day before yesterday as recent local days', () => {
    const now = new Date('2026-07-05T12:00:00+08:00');

    expect(isWithinRecentLocalAnalysisWindow('2026-07-05T00:10:00+08:00', now)).toBe(true);
    expect(isWithinRecentLocalAnalysisWindow('2026-07-04T23:10:00+08:00', now)).toBe(true);
    expect(isWithinRecentLocalAnalysisWindow('2026-07-03T08:00:00+08:00', now)).toBe(true);
    expect(isWithinRecentLocalAnalysisWindow('2026-07-02T23:59:59+08:00', now)).toBe(false);
  });
});
