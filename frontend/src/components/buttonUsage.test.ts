import { describe, expect, it } from 'vitest';

describe('application button styling', () => {
  it('uses themed components instead of unstyled native button declarations', () => {
    const views = import.meta.glob<string>('../**/*.vue', { query: '?raw', import: 'default', eager: true });
    const nativeButtons = Object.entries(views).filter(([, source]) => /<button(?:\s|>)/.test(source)).map(([path]) => path);
    expect(nativeButtons).toEqual([]);
  });
});
