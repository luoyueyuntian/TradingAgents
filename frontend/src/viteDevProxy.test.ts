// @vitest-environment node

import { describe, expect, it } from 'vitest';

import { createDevServerProxy, resolveDevBackendTarget } from '../vite.config';

describe('vite dev Docker backend proxy', () => {
  it('points local /api requests at the Docker backend by default', () => {
    expect(resolveDevBackendTarget({})).toBe('http://127.0.0.1:8000');
    expect(createDevServerProxy({})['/api'].target).toBe('http://127.0.0.1:8000');
  });

  it('allows overriding the backend target for alternate Docker ports', () => {
    const env = {
      TRADINGAGENTS_WEB_DEV_PROXY_TARGET: ' http://127.0.0.1:18000 ',
    };

    expect(resolveDevBackendTarget(env)).toBe('http://127.0.0.1:18000');
    expect(createDevServerProxy(env)['/api'].target).toBe('http://127.0.0.1:18000');
  });
});
