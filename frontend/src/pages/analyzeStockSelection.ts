export type StockMarketOption = {
  value: string;
  label: string;
};

export type StockCatalogOption = {
  market: string;
  symbol: string;
  name: string;
  exchange: string;
  label?: string;
};

export type AnalysisStockForm = {
  stock_market: string;
  ticker: string;
  date: string;
  analysts: string[];
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

export function marketProfileForStockMarket(market: string): string {
  return market === 'cn_a' ? 'cn_a' : 'default';
}

export function buildStockSearchPath(market: string, query = '', limit = 100): string {
  const params = new URLSearchParams();
  params.set('market', market);
  if (query.trim()) {
    params.set('q', query.trim());
  }
  params.set('limit', String(limit));
  return `/api/stocks?${params.toString()}`;
}

export function parseAnalysisDate(value: string): Date | null {
  if (!value) {
    return null;
  }
  const [yearText, monthText, dayText] = value.split('-');
  const year = Number(yearText);
  const month = Number(monthText);
  const day = Number(dayText);
  if (!Number.isInteger(year) || !Number.isInteger(month) || !Number.isInteger(day)) {
    return null;
  }
  return new Date(year, month - 1, day);
}

export function formatAnalysisDate(value: Date | null): string {
  if (!(value instanceof Date) || Number.isNaN(value.getTime())) {
    return '';
  }
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, '0');
  const day = String(value.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function normalizeStockOptions(rows: StockCatalogOption[]): Required<StockCatalogOption>[] {
  return rows.map((row) => {
    const parts = [row.symbol, row.name, row.exchange].filter(Boolean);
    return {
      market: row.market,
      symbol: row.symbol,
      name: row.name,
      exchange: row.exchange,
      label: row.label || parts.join(' · '),
    };
  });
}

export function buildAnalysisRequestPayload(form: AnalysisStockForm) {
  const toInt = (value: number | string) => Number(value);
  const toOptionalFloat = (value: number | string | null) => {
    if (value === null || value === '') {
      return null;
    }
    const parsed = Number(value);
    return Number.isNaN(parsed) ? null : parsed;
  };

  return {
    ticker: form.ticker.trim().toUpperCase(),
    date: form.date,
    analysts: form.analysts,
    llm_provider: form.llm_provider,
    quick_think_model: form.quick_think_model,
    deep_think_model: form.deep_think_model,
    research_depth: toInt(form.research_depth),
    output_language: form.output_language,
    market_profile: marketProfileForStockMarket(form.stock_market),
    max_risk_discuss_rounds: toInt(form.max_risk_discuss_rounds),
    max_recur_limit: toInt(form.max_recur_limit),
    checkpoint_enabled: form.checkpoint_enabled,
    benchmark_ticker: form.benchmark_ticker.trim() || null,
    backend_url: form.backend_url.trim() || null,
    temperature: toOptionalFloat(form.temperature),
    google_thinking_level: form.google_thinking_level || null,
    openai_reasoning_effort: form.openai_reasoning_effort || null,
    anthropic_effort: form.anthropic_effort || null,
  };
}
