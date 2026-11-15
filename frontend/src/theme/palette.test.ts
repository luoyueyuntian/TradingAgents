import { describe, expect, it } from 'vitest';
import { interfaceColors, palette } from './palette';

function luminance(hex: string) {
  const rgb = [1, 3, 5].map((offset) => parseInt(hex.slice(offset, offset + 2), 16) / 255).map((v) => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  return 0.2126 * rgb[0]! + 0.7152 * rgb[1]! + 0.0722 * rgb[2]!;
}
describe('three-tone interface palette', () => {
  it('keeps every severity within the same three color families', () => {
    const allowed = new Set([...Object.values(palette.brand), ...Object.values(palette.info), ...Object.values(palette.success), ...Object.values(palette.neutral)]);
    for (const scale of Object.values(interfaceColors)) for (const color of Object.values(scale)) expect(allowed.has(color)).toBe(true);
  });
  it('keeps neutral surfaces truly gray', () => {
    for (const color of Object.values(palette.neutral)) expect(color.slice(1,3) === color.slice(3,5) && color.slice(3,5) === color.slice(5,7)).toBe(true);
  });
  it('provides AA contrast for white primary and status button labels', () => {
    for (const color of [palette.brand[600], interfaceColors.red[500], interfaceColors.yellow[500], palette.info[500], palette.success[500]]) {
      expect(1.05 / (luminance(color) + 0.05)).toBeGreaterThanOrEqual(4.5);
    }
  });
  it('has no stray chromatic literals in application views', () => {
    const files = import.meta.glob<string>('../**/*.vue', { query: '?raw', import: 'default', eager: true });
    const allowed = new Set(Object.values(palette).flatMap((scale) => Object.values(scale)).map((color) => color.toLowerCase()));
    for (const [path, source] of Object.entries(files)) {
      for (const match of source.matchAll(/#[0-9a-fA-F]{3,8}\b/g)) {
        const color = match[0].toLowerCase();
        const hex = color.length === 4 ? '#' + [...color.slice(1)].map((part) => part + part).join('') : color;
        expect(allowed.has(hex), `${path}: ${hex}`).toBe(true);
      }
    }
  });

});
