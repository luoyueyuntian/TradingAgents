import { describe, expect, it } from 'vitest';

import metricGridSource from '../components/MetricGrid.vue?raw';
import analyzePageSource from './AnalyzePage.vue?raw';
import automationsPageSource from './AutomationsPage.vue?raw';
import dashboardPageSource from './DashboardPage.vue?raw';
import runsPageSource from './RunsPage.vue?raw';
import settingsPageSource from './SettingsPage.vue?raw';

describe('responsive page layout contracts', () => {
  it('uses explicit metric card breakpoints for dashboard and standard four-item groups', () => {
    expect(dashboardPageSource).toContain('layout="dashboard"');
    expect(metricGridSource).toContain("layout === 'dashboard'");
    expect(metricGridSource).toContain('uno-grid-cols-4 max-[1100px]:uno-grid-cols-2 max-[640px]:uno-grid-cols-1');
    expect(metricGridSource).not.toContain('uno-grid-cols-4 max-[1100px]:uno-grid-cols-3 max-[640px]:uno-grid-cols-1');
    expect(runsPageSource).toContain('uno-grid-cols-4 max-[1100px]:uno-grid-cols-2 max-[640px]:uno-grid-cols-1');
  });

  it('stacks analysis configuration above current run details', () => {
    expect(analyzePageSource).toContain('data-testid="analysis-layout"');
    expect(analyzePageSource).not.toContain('data-testid="analysis-layout" class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(320px,1fr))]');
  });

  it('stacks automation rule creation above the rules list', () => {
    expect(automationsPageSource).toContain('data-testid="automation-layout"');
    expect(automationsPageSource).not.toContain('data-testid="automation-layout" class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(320px,1fr))]');
  });

  it('does not render the run detail card until a run is selected', () => {
    expect(runsPageSource).toContain('<Card v-if="selectedRun"');
    expect(runsPageSource).not.toContain("{{ t('runs.selectRun') }}");
  });

  it('gives model, backend URL, and API key fields wider responsive tracks', () => {
    expect(settingsPageSource).toContain('data-testid="llm-settings-grid"');
    expect(settingsPageSource).toContain('data-testid="api-key-settings-grid"');
    expect(settingsPageSource).toContain('minmax(min(100%,320px),1fr)');
  });
});
