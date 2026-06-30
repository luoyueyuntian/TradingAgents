export type ReportSections = Record<string, string | null | undefined>;

export type DecisionHighlights = {
  finalRating: string;
  tradeAction: string;
  priceTarget: string;
  riskControl: string;
  summary: string;
};

export type InsightPanel = {
  key: 'evidence' | 'risks' | 'actions';
  items: string[];
};

export type InsightActionLabels = {
  action: string;
  entry: string;
  stopLoss: string;
  sizing: string;
};

export type LiveRunViewState = {
  agents: Record<string, string>;
  reportSections: Record<string, string>;
  currentReport: string;
  latestReportSection: string;
  terminalReport: string;
  status: string;
  signal: string;
  logLines: string[];
};

const DEFAULT_INSIGHT_ACTION_LABELS: InsightActionLabels = {
  action: 'Action',
  entry: 'Entry',
  stopLoss: 'Stop loss',
  sizing: 'Sizing',
};

export function createLiveRunViewState(): LiveRunViewState {
  return {
    agents: {},
    reportSections: {},
    currentReport: '',
    latestReportSection: '',
    terminalReport: '',
    status: '',
    signal: '',
    logLines: [],
  };
}

export function applyRunStreamEvent(
  state: LiveRunViewState,
  eventName: string,
  rawPayload: string,
  timestamp = new Date().toLocaleTimeString(),
): LiveRunViewState {
  const payload = parsePayload(rawPayload);
  const next: LiveRunViewState = {
    ...state,
    agents: { ...state.agents },
    reportSections: { ...state.reportSections },
    logLines: [...state.logLines],
  };

  if (eventName === 'agent_status') {
    const agent = stringValue(payload.agent);
    const status = stringValue(payload.status);
    if (agent && status) {
      next.agents[agent] = status;
      next.logLines.push(`${timestamp} agent_status: ${agent} ${status}`);
    }
    return next;
  }

  if (eventName === 'report_update') {
    const section = stringValue(payload.section);
    const content = stringValue(payload.content);
    if (section && content) {
      next.reportSections[section] = content;
      next.latestReportSection = section;
      next.currentReport = content;
      next.logLines.push(`${timestamp} report_update: ${sectionLabel(section)}`);
    }
    return next;
  }

  if (eventName === 'complete') {
    const signal = stringValue(payload.signal);
    next.status = 'completed';
    next.signal = signal;
    next.terminalReport = stringValue(payload.report);
    next.logLines.push(`${timestamp} complete: ${signal || 'completed'}`);
    return next;
  }

  if (eventName === 'cancelled') {
    const message = stringValue(payload.message) || 'Analysis cancelled';
    next.status = 'cancelled';
    next.logLines.push(`${timestamp} cancelled: ${message}`);
    return next;
  }

  if (eventName === 'error') {
    const message = stringValue(payload.message) || 'Analysis failed';
    next.status = 'failed';
    next.logLines.push(`${timestamp} error: ${message}`);
    return next;
  }

  if (eventName === 'progress') {
    const message = stringValue(payload.message);
    const toolCall = stringValue(payload.tool_call);
    if (!next.status || next.status === 'queued' || next.status === 'pending') {
      next.status = 'running';
    }
    next.logLines.push(`${timestamp} progress: ${message || toolCall || rawPayload}`);
    return next;
  }

  next.logLines.push(`${timestamp} ${eventName}: ${rawPayload}`);
  return next;
}

export function buildDecisionHighlights(
  sections: ReportSections,
  signal?: string | null,
): DecisionHighlights {
  const finalDecision = stringValue(sections.final_trade_decision);
  const traderPlan = stringValue(sections.trader_investment_plan);

  return {
    finalRating: extractField(finalDecision, 'Rating') || stringValue(signal),
    tradeAction: extractField(traderPlan, 'Action') || extractFinalTransaction(traderPlan),
    priceTarget: extractField(finalDecision, 'Price Target') || extractField(traderPlan, 'Entry Price'),
    riskControl: extractField(traderPlan, 'Stop Loss') || extractField(finalDecision, 'Time Horizon'),
    summary: extractField(finalDecision, 'Executive Summary')
      || extractField(finalDecision, 'Investment Thesis')
      || extractField(traderPlan, 'Reasoning'),
  };
}

export function buildInsightPanels(
  sections: ReportSections,
  actionLabels: InsightActionLabels = DEFAULT_INSIGHT_ACTION_LABELS,
): InsightPanel[] {
  const finalDecision = stringValue(sections.final_trade_decision);
  const traderPlan = stringValue(sections.trader_investment_plan);
  const investmentPlan = stringValue(sections.investment_plan);

  const investmentThesis = extractField(finalDecision, 'Investment Thesis');
  const reasoning = extractField(traderPlan, 'Reasoning');
  const rationale = extractField(investmentPlan, 'Rationale');
  const summary = extractField(finalDecision, 'Executive Summary');
  const strategicActions = extractField(investmentPlan, 'Strategic Actions');
  const risks = [
    ...riskSentences(investmentThesis),
    ...riskSentences(summary),
    ...riskSentences(reasoning),
    stopLossRisk(traderPlan),
  ].filter(Boolean);

  return [
    {
      key: 'evidence',
      items: compact([
        firstSentence(investmentThesis),
        firstSentence(reasoning),
        firstSentence(rationale),
      ]),
    },
    {
      key: 'risks',
      items: unique(risks.length ? risks : compact([stopLossRisk(traderPlan)])),
    },
    {
      key: 'actions',
      items: compact([
        labelled(actionLabels.action, extractField(traderPlan, 'Action') || extractFinalTransaction(traderPlan)),
        labelled(actionLabels.entry, extractField(traderPlan, 'Entry Price')),
        labelled(actionLabels.stopLoss, extractField(traderPlan, 'Stop Loss')),
        labelled(actionLabels.sizing, extractField(traderPlan, 'Position Sizing')),
        strategicActions,
      ]),
    },
  ];
}

export function extractField(text: string, label: string): string {
  const escaped = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = text.match(new RegExp(`^\\s*(?:\\*\\*)?${escaped}(?:\\*\\*)?\\s*:\\s*(.+)$`, 'im'));
  return stripMarkdown(match?.[1] || '');
}

export function extractFinalTransaction(text: string): string {
  const match = text.match(/FINAL TRANSACTION PROPOSAL:\s*\*{0,2}([A-Z]+)\*{0,2}/i);
  return stripMarkdown(match?.[1] || '');
}

function parsePayload(rawPayload: string): Record<string, unknown> {
  try {
    const parsed = JSON.parse(rawPayload);
    return parsed && typeof parsed === 'object' ? parsed as Record<string, unknown> : {};
  } catch {
    return {};
  }
}

function stringValue(value: unknown): string {
  if (value === null || value === undefined) {
    return '';
  }
  return String(value).trim();
}

function stripMarkdown(value: string): string {
  return value.replace(/\*\*/g, '').trim();
}

function sectionLabel(section: string): string {
  return section
    .replace(/_report$/, '')
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function compact(values: Array<string | undefined>): string[] {
  return values
    .map((value) => stringValue(value))
    .filter((value) => value.length > 0);
}

function unique(values: string[]): string[] {
  return Array.from(new Set(values));
}

function labelled(label: string, value: string): string {
  return value ? `${label}: ${value}` : '';
}

function firstSentence(value: string): string {
  return splitSentences(value)[0] || value;
}

function splitSentences(value: string): string[] {
  return stripMarkdown(value)
    .split(/(?<=[.!?。！？])\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function riskSentences(value: string): string[] {
  return splitSentences(value).filter((sentence) => (
    /risk|downside|valuation|guidance|slip|drawdown|loss|volatility|pressure|uncertain|uncertainty|风险|下行|估值|指引|回撤|亏损|波动|压力|不确定|压缩|下滑|跌破|止损/i
      .test(sentence)
  ));
}

function stopLossRisk(traderPlan: string): string {
  const stopLoss = extractField(traderPlan, 'Stop Loss');
  return stopLoss ? `Stop loss: ${stopLoss}` : '';
}
