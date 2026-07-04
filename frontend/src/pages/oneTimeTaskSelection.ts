export type ManualStockPick = {
  market: string;
  symbol: string;
  name: string;
  exchange: string;
};

export type SelectedGroup = {
  id: string;
  name: string;
  tickers: string[];
};

function normalizeSymbol(value: string): string {
  return value.trim().toUpperCase();
}

export function upsertManualStock(selected: ManualStockPick[], stock: ManualStockPick): ManualStockPick[] {
  const symbol = normalizeSymbol(stock.symbol);
  if (!symbol) {
    return selected;
  }

  const nextStock: ManualStockPick = {
    ...stock,
    market: stock.market.trim().toLowerCase(),
    symbol,
  };

  const existingIndex = selected.findIndex((item) => normalizeSymbol(item.symbol) === symbol);
  if (existingIndex === -1) {
    return [...selected, nextStock];
  }

  const nextSelected = [...selected];
  nextSelected[existingIndex] = nextStock;
  return nextSelected;
}

export function mergeResolvedTickers(options: {
  manualStocks: ManualStockPick[];
  selectedGroups: SelectedGroup[];
  includeWatchlist: boolean;
  watchlistTickers: string[];
}): string[] {
  const seen = new Set<string>();
  const resolved: string[] = [];

  const add = (value: string) => {
    const normalized = normalizeSymbol(value);
    if (!normalized || seen.has(normalized)) {
      return;
    }
    seen.add(normalized);
    resolved.push(normalized);
  };

  options.manualStocks.forEach((stock) => add(stock.symbol));
  options.selectedGroups.forEach((group) => group.tickers.forEach(add));
  if (options.includeWatchlist) {
    options.watchlistTickers.forEach(add);
  }

  return resolved;
}
