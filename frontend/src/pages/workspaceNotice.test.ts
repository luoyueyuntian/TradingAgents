import { describe, expect, it } from 'vitest';

import workspacePageSource from './WorkspacePage.vue?raw';

describe('workspace notice handling', () => {
  it('keeps import success notices alive across the post-import refresh', () => {
    expect(workspacePageSource).not.toContain("notice.value = '';");
    expect(workspacePageSource).toContain("notice.value = `${t('workspace.importWorkspace')}: ${result.mode}`;");
  });
});
