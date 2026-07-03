import { describe, expect, it } from 'vitest';
import analyzePageSource from './AnalyzePage.vue?raw';
import automationsPageSource from './AutomationsPage.vue?raw';
import portfolioPageSource from './PortfolioPage.vue?raw';
import runsPageSource from './RunsPage.vue?raw';
import settingsPageSource from './SettingsPage.vue?raw';
import workspacePageSource from './WorkspacePage.vue?raw';

describe('viewer role gating', () => {
  it('ties write controls to session.canWrite on operational pages', () => {
    const expectations = [
      analyzePageSource,
      runsPageSource,
      portfolioPageSource,
      workspacePageSource,
      automationsPageSource,
    ];

    for (const source of expectations) {
      expect(source).toContain('session.canWrite.value');
    }
  });

  it('keeps settings save controls admin-only', () => {
    expect(settingsPageSource).toContain('session.isAdmin.value');
    expect(settingsPageSource).toContain("t('common.save')");
  });
});
