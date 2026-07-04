// Dynamic API payloads are intentionally represented as JSON-like bags here.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type JsonRecord = Record<string, any>;

const ISO_DATE_TIME_WITHOUT_ZONE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d{1,3})?)?$/;

export function asArray<T = JsonRecord>(value: unknown): T[] {
  return Array.isArray(value) ? value as T[] : [];
}

function localTimeZone(): string | undefined {
  return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined;
}

function padTwoDigits(value: number): string {
  return String(value).padStart(2, '0');
}

export function parseDateTime(value: unknown): Date | null {
  if (!value) {
    return null;
  }
  if (typeof value === 'number' && Number.isFinite(value)) {
    const date = new Date(value);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  if (typeof value === 'string' && /^\d+$/.test(value.trim())) {
    const numeric = Number(value.trim());
    const date = new Date(numeric);
    return Number.isNaN(date.getTime()) ? null : date;
  }
  const text = String(value).trim();
  if (!text) {
    return null;
  }
  const normalized = ISO_DATE_TIME_WITHOUT_ZONE.test(text) ? `${text}Z` : text;
  const date = new Date(normalized);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date;
}

export function formatDateTime(value: unknown): string {
  if (!value) {
    return 'n/a';
  }
  const text = String(value);
  const date = parseDateTime(text);
  if (!date) {
    return text;
  }
  const timeZone = localTimeZone();
  return timeZone
    ? date.toLocaleString(undefined, { timeZone })
    : date.toLocaleString();
}

export function formatDateTimeInputValue(value: unknown): string {
  const date = parseDateTime(value);
  if (!date) {
    return '';
  }
  const year = date.getFullYear();
  const month = padTwoDigits(date.getMonth() + 1);
  const day = padTwoDigits(date.getDate());
  const hours = padTwoDigits(date.getHours());
  const minutes = padTwoDigits(date.getMinutes());
  return `${year}-${month}-${day}T${hours}:${minutes}`;
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
