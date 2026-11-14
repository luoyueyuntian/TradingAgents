import { describe, expect, it } from 'vitest';

import { passwordChangeErrorKey } from './passwordChangeFeedback';

describe('password change feedback', () => {
  it.each([
    ['Invalid credentials', 'auth.passwordChangeWrongCurrent'],
    ['Unauthorized', 'auth.passwordChangeSessionExpired'],
    ['Password must be at least 10 characters', 'auth.passwordChangeTooShort'],
    ['Password must include at least two character classes', 'auth.passwordChangeComplexity'],
    ['Password must not match username', 'auth.passwordChangeMatchesIdentity'],
    ['Password must not match email', 'auth.passwordChangeMatchesIdentity'],
    ['Password must not be blank', 'auth.passwordChangeMissingNew'],
    ['Failed to fetch', 'auth.passwordChangeNetwork'],
    ['Internal Server Error', 'auth.passwordChangeFailed'],
  ])('turns %s into actionable feedback', (message, key) => {
    expect(passwordChangeErrorKey(new Error(message))).toBe(key);
  });
  it('does not expose an arbitrary server response', () => {
    expect(passwordChangeErrorKey({ detail: 'internal detail' })).toBe('auth.passwordChangeFailed');
  });
});
