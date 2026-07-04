import type { ManualStockPick } from './oneTimeTaskSelection';

export type OneTimeTaskFormState = {
  name: string;
  scheduledFor: string;
  analysisDate: string;
  manualStocks: ManualStockPick[];
  selectedGroupIds: string[];
  includeWatchlist: boolean;
  llm_provider: string;
  quick_think_model: string;
  deep_think_model: string;
  research_depth: number | string;
  output_language: string;
  market_profile: string;
  max_risk_discuss_rounds: number | string;
  max_recur_limit: number | string;
  checkpoint_enabled: boolean;
  benchmark_ticker: string;
  backend_url: string;
  temperature: number | string | null;
  google_thinking_level: string;
  openai_reasoning_effort: string;
  anthropic_effort: string;
};

export type OneTimeTaskAnalysisConfig = {
  analysts: string[];
  llm_provider: string;
  deep_think_model?: string | null;
  quick_think_model?: string | null;
  research_depth: number;
  output_language: string;
  market_profile?: string | null;
  max_risk_discuss_rounds?: number | null;
  max_recur_limit?: number | null;
  checkpoint_enabled?: boolean | null;
  benchmark_ticker?: string | null;
  backend_url?: string | null;
  temperature?: number | null;
  google_thinking_level?: string | null;
  openai_reasoning_effort?: string | null;
  anthropic_effort?: string | null;
};

export type OneTimeTaskCreatePayload = {
  name: string;
  scheduled_for: string;
  analysis_date: string;
  manual_stocks: ManualStockPick[];
  group_ids: string[];
  include_watchlist: boolean;
  analysis_config: OneTimeTaskAnalysisConfig;
};

function toOptionalInt(value: number | string) {
  if (value === '') {
    return null;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function toOptionalFloat(value: number | string | null) {
  if (value === null || value === '') {
    return null;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

export function buildOneTimeTaskPayload(form: OneTimeTaskFormState): OneTimeTaskCreatePayload {
  return {
    name: form.name.trim(),
    scheduled_for: form.scheduledFor.trim(),
    analysis_date: form.analysisDate,
    manual_stocks: form.manualStocks.map((stock) => ({
      market: stock.market,
      symbol: stock.symbol.trim().toUpperCase(),
      name: stock.name,
      exchange: stock.exchange,
    })),
    group_ids: [...form.selectedGroupIds],
    include_watchlist: form.includeWatchlist,
    analysis_config: {
      analysts: ['market', 'social', 'news', 'fundamentals'],
      llm_provider: form.llm_provider,
      quick_think_model: form.quick_think_model.trim() || null,
      deep_think_model: form.deep_think_model.trim() || null,
      research_depth: Number(form.research_depth),
      output_language: form.output_language,
      market_profile: form.market_profile || null,
      max_risk_discuss_rounds: toOptionalInt(form.max_risk_discuss_rounds),
      max_recur_limit: toOptionalInt(form.max_recur_limit),
      checkpoint_enabled: form.checkpoint_enabled,
      benchmark_ticker: form.benchmark_ticker.trim() || null,
      backend_url: form.backend_url.trim() || null,
      temperature: toOptionalFloat(form.temperature),
      google_thinking_level: form.google_thinking_level || null,
      openai_reasoning_effort: form.openai_reasoning_effort || null,
      anthropic_effort: form.anthropic_effort || null,
    },
  };
}
