import { type JsonRecord } from '../utils/format';

export type RunCompanyGroup = {
  group_key: string;
  company_name: string;
  asset_type: string;
  tickers: string[];
  run_count: number;
  latest_run_id?: string | null;
  latest_status?: string | null;
  latest_signal?: string | null;
  latest_date?: string | null;
  latest_created_at?: number | null;
  recent_runs: JsonRecord[];
};

export type RunCompanyGroupPage = {
  items: RunCompanyGroup[];
  page: number;
  page_size: number;
  total_count: number;
};

export function buildRunCompanyGroupsPath(input: {
  q: string;
  status: string;
  archived: string;
  page: number;
  pageSize: number;
}): string {
  const params = new URLSearchParams();
  if (input.q.trim()) {
    params.set('q', input.q.trim());
  }
  if (input.status) {
    params.set('status', input.status);
  }
  if (input.archived) {
    params.set('archived', input.archived);
  }
  params.set('page', String(input.page));
  params.set('page_size', String(input.pageSize));
  return `/api/runs/company-groups?${params.toString()}`;
}
