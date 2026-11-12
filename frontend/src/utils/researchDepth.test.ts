import { describe, expect, it } from 'vitest';

import type { MessageKey } from '../i18n';
import { formatResearchDepth } from './researchDepth';

describe('formatResearchDepth', () => {
  const messages: Partial<Record<MessageKey, string>> = {
    'analysis.depthShallow': '浅层（1 轮）',
    'analysis.depthMedium': '中等（3 轮）',
    'analysis.depthDeep': '深度（5 轮）',
    'common.na': '无',
  };
  const translate = (key: MessageKey) => messages[key] ?? key;

  it('formats known depth presets into localized labels', () => {
    expect(formatResearchDepth(1, translate)).toBe('浅层（1 轮）');
    expect(formatResearchDepth('3', translate)).toBe('中等（3 轮）');
    expect(formatResearchDepth(5, translate)).toBe('深度（5 轮）');
  });

  it('falls back to the raw value or localized n/a when needed', () => {
    expect(formatResearchDepth(7, translate)).toBe('7');
    expect(formatResearchDepth(null, translate)).toBe('无');
  });
});
