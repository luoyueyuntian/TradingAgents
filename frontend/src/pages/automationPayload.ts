export type AutomationFormState = {
  name: string;
  source: string;
  cadence: string;
  weekday: string;
  time: string;
  tickers: string;
  enabled: boolean;
};

export type AutomationAnalysisConfig = {
  analysts: string[];
  llm_provider: string;
  research_depth: number;
  output_language: string;
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
  research_depth: 1,
  output_language: 'English',
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
    },
  };
}
