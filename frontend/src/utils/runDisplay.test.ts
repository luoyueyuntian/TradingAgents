import { describe, expect, it } from 'vitest';

import {
  applyRunStreamEvent,
  buildDecisionHighlights,
  buildInsightPanels,
  createLiveRunViewState,
} from './runDisplay';

describe('run display helpers', () => {
  it('updates live progress state from streamed run events', () => {
    let state = createLiveRunViewState();

    state = applyRunStreamEvent(state, 'agent_status', JSON.stringify({
      agent: 'Market Analyst',
      status: 'completed',
    }), '09:30:00');
    state = applyRunStreamEvent(state, 'report_update', JSON.stringify({
      section: 'market_report',
      content: '## Market\nMomentum is improving.',
    }), '09:31:00');
    state = applyRunStreamEvent(state, 'complete', JSON.stringify({
      signal: 'Buy',
      report: '## Final\n**Rating**: Buy',
    }), '09:32:00');

    expect(state.agents).toEqual({ 'Market Analyst': 'completed' });
    expect(state.reportSections.market_report).toBe('## Market\nMomentum is improving.');
    expect(state.currentReport).toBe('## Market\nMomentum is improving.');
    expect(state.status).toBe('completed');
    expect(state.signal).toBe('Buy');
    expect(state.terminalReport).toBe('## Final\n**Rating**: Buy');
    expect(state.logLines).toEqual([
      '09:30:00 agent_status: Market Analyst completed',
      '09:31:00 report_update: Market',
      '09:32:00 complete: Buy',
    ]);
  });

  it('marks queued live state as running when progress begins', () => {
    let state = {
      ...createLiveRunViewState(),
      status: 'queued',
    };

    state = applyRunStreamEvent(state, 'progress', JSON.stringify({
      message: 'Starting analysis for AAPL on 2026-06-30',
    }), '09:30:10');

    expect(state.status).toBe('running');
    expect(state.logLines).toEqual([
      '09:30:10 progress: Starting analysis for AAPL on 2026-06-30',
    ]);
  });

  it('builds decision highlights from structured report fields', () => {
    const highlights = buildDecisionHighlights({
      final_trade_decision: [
        '**Rating**: Overweight',
        '',
        '**Executive Summary**: Add gradually while monitoring guidance.',
        '',
        '**Price Target**: 120',
        '',
        '**Time Horizon**: 3-6 months',
      ].join('\n'),
      trader_investment_plan: [
        '**Action**: Buy',
        '',
        '**Entry Price**: 100',
        '',
        '**Stop Loss**: 92',
      ].join('\n'),
    }, 'Buy');

    expect(highlights).toEqual({
      finalRating: 'Overweight',
      tradeAction: 'Buy',
      priceTarget: '120',
      riskControl: '92',
      summary: 'Add gradually while monitoring guidance.',
    });
  });

  it('extracts evidence, risk, and action panels from saved reports', () => {
    const panels = buildInsightPanels({
      investment_plan: '**Strategic Actions**: Accumulate in tranches around pullbacks.',
      trader_investment_plan: [
        '**Action**: Buy',
        '',
        '**Reasoning**: Momentum confirms the breakout and demand remains resilient.',
        '',
        '**Entry Price**: 100',
        '',
        '**Stop Loss**: 92',
        '',
        '**Position Sizing**: 5% of portfolio',
      ].join('\n'),
      final_trade_decision: [
        '**Rating**: Buy',
        '',
        '**Executive Summary**: Build the position gradually over the next quarter.',
        '',
        '**Investment Thesis**: Revenue acceleration and strong demand support upside. Main risk is valuation compression if guidance slips.',
      ].join('\n'),
    });

    expect(panels.map((panel) => panel.key)).toEqual(['evidence', 'risks', 'actions']);
    expect(panels.find((panel) => panel.key === 'evidence')?.items.join(' ')).toContain('Revenue acceleration');
    expect(panels.find((panel) => panel.key === 'risks')?.items.join(' ')).toContain('valuation compression');
    expect(panels.find((panel) => panel.key === 'actions')?.items).toEqual([
      'Action: Buy',
      'Entry: 100',
      'Stop loss: 92',
      'Sizing: 5% of portfolio',
      'Accumulate in tranches around pullbacks.',
    ]);
  });

  it('uses localized action labels when building insight panels', () => {
    const panels = buildInsightPanels({
      trader_investment_plan: [
        '**Action**: Buy',
        '**Entry Price**: 100',
        '**Stop Loss**: 92',
        '**Position Sizing**: 5% of portfolio',
      ].join('\n'),
    }, {
      action: '操作',
      entry: '入场',
      stopLoss: '止损',
      sizing: '仓位',
    });

    expect(panels.find((panel) => panel.key === 'actions')?.items).toEqual([
      '操作: Buy',
      '入场: 100',
      '止损: 92',
      '仓位: 5% of portfolio',
    ]);
  });

  it('extracts Chinese risk statements from final decisions', () => {
    const panels = buildInsightPanels({
      final_trade_decision: [
        '**Rating**: Buy',
        '',
        '**Investment Thesis**: 收入增长和需求改善支持上行。主要风险是估值压缩，如果指引下滑，股价可能回撤。',
      ].join('\n'),
    });

    expect(panels.find((panel) => panel.key === 'risks')?.items.join(' ')).toContain('估值压缩');
    expect(panels.find((panel) => panel.key === 'risks')?.items.join(' ')).toContain('指引下滑');
  });
});
