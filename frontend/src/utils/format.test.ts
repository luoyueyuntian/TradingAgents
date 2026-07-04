import { afterEach, describe, expect, it, vi } from 'vitest';

import { formatDateTime, parseDateTime } from './format';

describe('format helpers', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('treats ISO date-time strings without an explicit timezone as UTC', () => {
    expect(parseDateTime('2026-07-04T09:00:00')?.toISOString()).toBe('2026-07-04T09:00:00.000Z');
    expect(parseDateTime('2026-07-04T09:00:00.250')?.toISOString()).toBe('2026-07-04T09:00:00.250Z');
  });

  it('formats date-time values in the resolved local timezone', () => {
    const toLocaleStringSpy = vi.spyOn(Date.prototype, 'toLocaleString').mockImplementation(() => 'localized');
    vi.spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions').mockReturnValue({
      locale: 'en-US',
      calendar: 'gregory',
      numberingSystem: 'latn',
      timeZone: 'America/New_York',
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
    });

    expect(formatDateTime('2026-07-04T09:00:00Z')).toBe('localized');
    expect(toLocaleStringSpy).toHaveBeenCalledWith(undefined, { timeZone: 'America/New_York' });
  });

  it('parses and formats unix millisecond timestamps', () => {
    const timestamp = 1_783_623_600_000;
    const toLocaleStringSpy = vi.spyOn(Date.prototype, 'toLocaleString').mockImplementation(() => 'localized-ms');
    vi.spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions').mockReturnValue({
      locale: 'en-US',
      calendar: 'gregory',
      numberingSystem: 'latn',
      timeZone: 'Asia/Shanghai',
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
    });

    expect(parseDateTime(timestamp)?.getTime()).toBe(timestamp);
    expect(formatDateTime(timestamp)).toBe('localized-ms');
    expect(toLocaleStringSpy).toHaveBeenCalledWith(undefined, { timeZone: 'Asia/Shanghai' });
  });
});
