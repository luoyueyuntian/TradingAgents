import { parseDateTime, type JsonRecord } from '../utils/format';

export type TickerRunHistoryPage = {
  ticker: string;
  company_name?: string | null;
  latest_created_at?: number | string | null;
  has_active_run: boolean;
  active_run_id?: string | null;
  active_run_status?: string | null;
  page: number;
  page_size: number;
  total_count: number;
  items: JsonRecord[];
};

export function buildTickerHistoryPath(input: { ticker: string; page: number; pageSize: number }): string {
  const params = new URLSearchParams({
    ticker: input.ticker.trim().toUpperCase(),
    page: String(input.page),
    page_size: String(input.pageSize),
  });
  return `/api/runs/ticker-history?${params.toString()}`;
}

export function isWithinRecentLocalAnalysisWindow(
  value: string | number | null | undefined,
  now = new Date(),
): boolean {
  const target = parseDateTime(value);
  if (!target) {
    return false;
  }
  const anchor = new Date(now);
  anchor.setHours(0, 0, 0, 0);
  const recentDays = [0, 1, 2].map((offset) => {
    const candidate = new Date(anchor);
    candidate.setDate(anchor.getDate() - offset);
    return candidate.toDateString();
  });
  return recentDays.includes(target.toDateString());
}
