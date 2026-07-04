export type AutomationFormState = {
  name: string;
  source: string;
  cadence: string;
  weekday: string;
  time: string;
  tickers: string;
  enabled: boolean;
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

export type AutomationAnalysisConfig = {
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

export type AutomationCreatePayload = Record<string, unknown> & {
  name: string;
  source: string;
  cadence: string;
  weekday: string | null;
  time_of_day: string;
  tickers: string[];
  enabled: boolean;
  analysis_config: AutomationAnalysisConfig;
};

const DEFAULT_ANALYSIS_CONFIG: AutomationAnalysisConfig = {
  analysts: ['market', 'social', 'news', 'fundamentals'],
  llm_provider: 'openai',
  deep_think_model: null,
  quick_think_model: null,
  research_depth: 1,
  output_language: 'English',
  market_profile: 'default',
  max_risk_discuss_rounds: 1,
  max_recur_limit: 100,
  checkpoint_enabled: false,
  benchmark_ticker: null,
  backend_url: null,
  temperature: null,
  google_thinking_level: null,
  openai_reasoning_effort: null,
  anthropic_effort: null,
};

export function parseAutomationTickers(value: string): string[] {
  const seen = new Set<string>();
  return value
    .split(/[,\s]+/)
    .map((ticker) => ticker.trim().toUpperCase())
    .filter((ticker) => {
      if (!ticker || seen.has(ticker)) {
        return false;
      }
      seen.add(ticker);
      return true;
    });
}

export function buildAutomationPayload(form: AutomationFormState): AutomationCreatePayload {
  const toInt = (value: number | string) => Number(value);
  const toOptionalInt = (value: number | string) => {
    if (value === '') return null;
    const parsed = Number(value);
    return Number.isNaN(parsed) ? null : parsed;
  };
  const toOptionalFloat = (value: number | string | null) => {
    if (value === null || value === '') return null;
    const parsed = Number(value);
    return Number.isNaN(parsed) ? null : parsed;
  };

  return {
    name: form.name.trim(),
    source: form.source,
    cadence: form.cadence,
    weekday: form.cadence === 'weekly' ? form.weekday : null,
    time_of_day: form.time.trim() || '09:00',
    tickers: form.source === 'manual' ? parseAutomationTickers(form.tickers) : [],
    enabled: form.enabled,
    analysis_config: {
      ...DEFAULT_ANALYSIS_CONFIG,
      analysts: [...DEFAULT_ANALYSIS_CONFIG.analysts],
      llm_provider: form.llm_provider,
      quick_think_model: form.quick_think_model.trim() || null,
      deep_think_model: form.deep_think_model.trim() || null,
      research_depth: toInt(form.research_depth),
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
