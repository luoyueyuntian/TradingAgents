// Dynamic API payloads are intentionally represented as JSON-like bags here.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type JsonRecord = Record<string, any>;

export function asArray<T = JsonRecord>(value: unknown): T[] {
  return Array.isArray(value) ? value as T[] : [];
}

export function formatDateTime(value: unknown): string {
  if (!value) {
    return 'n/a';
  }
  const text = String(value);
  const date = new Date(text);
  if (Number.isNaN(date.getTime())) {
    return text;
  }
  return date.toLocaleString();
}

export function compactText(value: unknown, fallback = 'n/a'): string {
  if (value === null || value === undefined || value === '') {
    return fallback;
  }
  return String(value);
}

export function signalSeverity(signal: unknown): 'success' | 'info' | 'warn' | 'danger' | 'secondary' {
  const text = String(signal || '').toLowerCase();
  if (text.includes('buy') || text.includes('overweight') || text.includes('bull')) {
    return 'success';
  }
  if (text.includes('sell') || text.includes('underweight') || text.includes('bear')) {
    return 'danger';
  }
  if (text.includes('hold') || text.includes('neutral')) {
    return 'info';
  }
  if (text.includes('fail') || text.includes('cancel')) {
    return 'warn';
  }
  return 'secondary';
}
