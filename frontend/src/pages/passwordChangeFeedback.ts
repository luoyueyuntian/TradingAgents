export function passwordChangeErrorKey(error: unknown) {
  const message = error instanceof Error ? error.message : '';
  switch (message) {
    case 'Invalid credentials': return 'auth.passwordChangeWrongCurrent';
    case 'Unauthorized': return 'auth.passwordChangeSessionExpired';
    case 'Password must be at least 10 characters': return 'auth.passwordChangeTooShort';
    case 'Password must include at least two character classes': return 'auth.passwordChangeComplexity';
    case 'Password must not match username':
    case 'Password must not match email': return 'auth.passwordChangeMatchesIdentity';
    case 'Password must not be blank': return 'auth.passwordChangeMissingNew';
  }
  if (error instanceof TypeError || /fetch|network|connection|timeout/i.test(message)) {
    return 'auth.passwordChangeNetwork';
  }
  if (message === 'User account is disabled' || message === 'User account has expired' || /Tenant.*(disabled|expired|not found)/i.test(message)) {
    return 'auth.passwordChangeAccountUnavailable';
  }
  return 'auth.passwordChangeFailed';
}
