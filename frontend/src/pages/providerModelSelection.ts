import type { JsonRecord } from '../utils/format';

export const CUSTOM_MODEL_OPTION_VALUE = 'custom';

export function hasCustomModelOption(options: JsonRecord[] | undefined): boolean {
  return Boolean(options?.some((option) => String(option.value || '') === CUSTOM_MODEL_OPTION_VALUE));
}

export function isPresetModelOption(options: JsonRecord[] | undefined, model: unknown): boolean {
  const value = String(model || '');
  if (!value || value === CUSTOM_MODEL_OPTION_VALUE) {
    return false;
  }
  return Boolean(options?.some((option) => String(option.value || '') === value));
}

export function firstPresetModelValue(options: JsonRecord[] | undefined): string {
  return String(
    options?.find((option) => String(option.value || '') !== CUSTOM_MODEL_OPTION_VALUE)?.value || '',
  );
}

export function displayedModelSelection(options: JsonRecord[] | undefined, model: unknown): string {
  if (isPresetModelOption(options, model)) {
    return String(model);
  }
  if (hasCustomModelOption(options)) {
    return CUSTOM_MODEL_OPTION_VALUE;
  }
  return firstPresetModelValue(options);
}

export function normalizeModelValueForProvider(
  options: JsonRecord[] | undefined,
  model: unknown,
  force = false,
): string {
  const value = String(model || '');
  if (force) {
    return firstPresetModelValue(options);
  }
  if (isPresetModelOption(options, value)) {
    return value;
  }
  if (hasCustomModelOption(options) && value && value !== CUSTOM_MODEL_OPTION_VALUE) {
    return value;
  }
  return firstPresetModelValue(options);
}

export function nextModelValueFromSelection(
  options: JsonRecord[] | undefined,
  currentModel: unknown,
  selection: unknown,
): string {
  const selectedValue = String(selection || '');
  if (selectedValue === CUSTOM_MODEL_OPTION_VALUE) {
    return isPresetModelOption(options, currentModel) || String(currentModel || '') === CUSTOM_MODEL_OPTION_VALUE
      ? ''
      : String(currentModel || '');
  }
  return selectedValue;
}
