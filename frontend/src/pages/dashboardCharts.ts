import { asArray, type JsonRecord } from '../utils/format';
export type ChartRow = { label: string; value: number };
function validCount(value: unknown): value is number { return typeof value === 'number' && Number.isFinite(value) && value >= 0; }
export function activityRows(value: unknown): ChartRow[] {
  return asArray(value).filter(row => /^\d{4}-\d{2}-\d{2}$/.test(String(row.date)) && validCount(row.total_runs))
    .map(row => ({ label: String(row.date), value: row.total_runs as number }))
    .sort((a,b) => a.label.localeCompare(b.label)).slice(-14);
}
export function bucketRows(value: unknown, limit = Infinity): ChartRow[] {
  return asArray(value).filter(row => typeof row.label === 'string' && row.label && validCount(row.value) && row.value > 0)
    .map(row => ({ label: row.label as string, value: row.value as number }))
    .sort((a,b) => b.value-a.value).slice(0,limit);
}
export function successPercentage(summary: JsonRecord | undefined): number | null {
  if (!summary || !validCount(summary.terminal_runs) || !summary.terminal_runs || typeof summary.success_rate !== 'number' || !Number.isFinite(summary.success_rate) || summary.success_rate < 0 || summary.success_rate > 1) return null;
  return Math.round(summary.success_rate*1000)/10;
}
