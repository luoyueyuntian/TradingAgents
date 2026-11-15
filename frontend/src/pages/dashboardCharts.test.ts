import { describe, expect, it } from 'vitest';
import { activityRows, bucketRows, successPercentage } from './dashboardCharts';

describe('dashboard chart data', () => {
  it('sorts the existing activity dates without inventing missing dates', () => {
    expect(activityRows([{date:'2026-11-15',total_runs:3},{date:'2026-07-01',total_runs:2}])).toEqual([{label:'2026-07-01',value:2},{label:'2026-11-15',value:3}]);
  });
  it('omits invalid counts and keeps explicitly reported zero days', () => {
    expect(activityRows([{date:'invalid',total_runs:4},{date:'2026-11-15',total_runs:0},{date:'2026-11-14',total_runs:-1}])).toEqual([{label:'2026-11-15',value:0}]);
    expect(bucketRows([{label:'AAPL',value:2},{label:'BAD',value:NaN},{label:'EMPTY',value:0}],5)).toEqual([{label:'AAPL',value:2}]);
  });
  it('does not pretend a missing terminal population has a success rate', () => {
    expect(successPercentage({terminal_runs:0,success_rate:0})).toBeNull();
    expect(successPercentage({terminal_runs:10,success_rate:0.8})).toBe(80);
  });
});
