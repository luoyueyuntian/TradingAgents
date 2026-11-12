import type { MessageKey } from '../i18n';

type ResearchDepthMessageKey = 'analysis.depthShallow' | 'analysis.depthMedium' | 'analysis.depthDeep' | 'common.na';
type Translate = (key: MessageKey) => string;

const DEPTH_LABELS: Record<number, ResearchDepthMessageKey> = {
  1: 'analysis.depthShallow',
  3: 'analysis.depthMedium',
  5: 'analysis.depthDeep',
};

function normalizeResearchDepth(value: unknown): number | null {
  if (typeof value === 'number' && Number.isInteger(value)) {
    return value;
  }
  if (typeof value === 'string' && /^\d+$/.test(value.trim())) {
    return Number(value.trim());
  }
  return null;
}

export function formatResearchDepth(value: unknown, translate: Translate): string {
  const normalized = normalizeResearchDepth(value);
  if (normalized === null) {
    return translate('common.na');
  }
  const labelKey = DEPTH_LABELS[normalized];
  return labelKey ? translate(labelKey) : String(normalized);
}
