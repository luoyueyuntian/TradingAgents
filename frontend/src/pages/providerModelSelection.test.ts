import { describe, expect, it } from 'vitest';

import {
  displayedModelSelection,
  nextModelValueFromSelection,
  normalizeModelValueForProvider,
} from './providerModelSelection';

const customOnlyOptions = [{ label: 'Custom model ID', value: 'custom' }];
const presetAndCustomOptions = [
  { label: 'GPT-5.4 Mini', value: 'gpt-5.4-mini' },
  { label: 'Custom model ID', value: 'custom' },
];

describe('provider model selection helpers', () => {
  it('shows the custom selection for custom-only providers while preserving the actual model id', () => {
    expect(displayedModelSelection(customOnlyOptions, 'moonshot-v1-8k')).toBe('custom');
    expect(normalizeModelValueForProvider(customOnlyOptions, 'moonshot-v1-8k')).toBe('moonshot-v1-8k');
    expect(normalizeModelValueForProvider(customOnlyOptions, '', true)).toBe('');
  });

  it('falls back to the first preset model for invalid preset selections', () => {
    expect(displayedModelSelection(presetAndCustomOptions, 'gpt-5.4-mini')).toBe('gpt-5.4-mini');
    expect(normalizeModelValueForProvider(presetAndCustomOptions, '')).toBe('gpt-5.4-mini');
    expect(normalizeModelValueForProvider(presetAndCustomOptions, 'custom')).toBe('gpt-5.4-mini');
  });

  it('switches into custom mode without persisting the literal custom sentinel', () => {
    expect(nextModelValueFromSelection(presetAndCustomOptions, 'gpt-5.4-mini', 'custom')).toBe('');
    expect(nextModelValueFromSelection(customOnlyOptions, 'moonshot-v1-8k', 'custom')).toBe('moonshot-v1-8k');
  });
});
