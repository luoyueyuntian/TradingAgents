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
  research_depth: number;
  output_language: string;
  market_profile: string;
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
  return {
    ticker: form.ticker.trim().toUpperCase(),
    date: form.date,
    analysts: form.analysts,
    llm_provider: form.llm_provider,
    quick_think_model: form.quick_think_model,
    deep_think_model: form.deep_think_model,
    research_depth: form.research_depth,
    output_language: form.output_language,
    market_profile: marketProfileForStockMarket(form.stock_market),
  };
}
