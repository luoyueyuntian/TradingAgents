import { describe, expect, it } from 'vitest';

import metricGridSource from '../components/MetricGrid.vue?raw';
import reportMarkdownSource from '../components/ReportMarkdown.vue?raw';
import analyzePageSource from './AnalyzePage.vue?raw';
import automationsPageSource from './AutomationsPage.vue?raw';
import dashboardPageSource from './DashboardPage.vue?raw';
import runDetailPageSource from './RunDetailPage.vue?raw';
import runsPageSource from './RunsPage.vue?raw';
import settingsPageSource from './SettingsPage.vue?raw';

describe('responsive page layout contracts', () => {
  it('uses explicit metric card breakpoints for dashboard and standard four-item groups', () => {
    expect(dashboardPageSource).toContain('layout="dashboard"');
    expect(metricGridSource).toContain("layout === 'dashboard'");
    expect(metricGridSource).toContain('uno-grid-cols-4 max-[1100px]:uno-grid-cols-2 max-[640px]:uno-grid-cols-1');
    expect(metricGridSource).not.toContain('uno-grid-cols-4 max-[1100px]:uno-grid-cols-3 max-[640px]:uno-grid-cols-1');
    expect(runDetailPageSource).toContain('uno-grid-cols-4 max-[1100px]:uno-grid-cols-2 max-[640px]:uno-grid-cols-1');
  });

  it('stacks analysis configuration above current run details', () => {
    expect(analyzePageSource).toContain('data-testid="analysis-layout"');
    expect(analyzePageSource).not.toContain('data-testid="analysis-layout" class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(320px,1fr))]');
  });

  it('keeps analysis select fields shrinkable when long option labels are selected', () => {
    expect(analyzePageSource).toContain("const formSelectPt = {");
    expect(analyzePageSource).toContain("root: { class: 'uno-min-w-0' }");
    expect(analyzePageSource).toContain("label: { class: 'uno-block uno-min-w-0 uno-max-w-full uno-overflow-hidden uno-text-ellipsis uno-whitespace-nowrap' }");
    expect(analyzePageSource).toContain(':pt="formSelectPt"');
    expect(analyzePageSource).not.toContain('const modelSelectPt = {');
    expect(analyzePageSource).toContain('data-testid="analysis-form-row-primary"');
    expect(analyzePageSource).toContain('data-testid="analysis-form-row-models"');
    expect(analyzePageSource).toContain('uno-grid uno-min-w-0 uno-gap-[0.35rem]');
    expect(analyzePageSource).toContain('class="uno-w-full uno-min-w-0"');
  });

  it('keeps language in the primary analysis row and centers the start action on its own row', () => {
    const primaryRow = analyzePageSource.split('data-testid="analysis-form-row-primary"')[1]?.split('data-testid="analysis-form-row-models"')[0] || '';
    const actionRow = analyzePageSource.split('data-testid="analysis-form-row-actions"')[1]?.split('<details')[0] || '';

    expect(primaryRow).toContain("{{ t('common.language') }}");
    expect(actionRow).not.toContain("{{ t('common.language') }}");
    expect(actionRow).toContain('uno-justify-center');
    expect(actionRow).not.toContain('uno-items-end');
    expect(actionRow).not.toContain('uno-flex-1');
  });

  it('stacks automation rule creation above the rules list', () => {
    expect(automationsPageSource).toContain('data-testid="automation-layout"');
    expect(automationsPageSource).not.toContain('data-testid="automation-layout" class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(320px,1fr))]');
  });

  it('opens run details on a secondary route instead of expanding inline', () => {
    expect(runsPageSource).toContain('data-testid="runs-company-group-card"');
    expect(runsPageSource).toContain('@row-click="openRunDetail($event.data)"');
    expect(runsPageSource).toContain("router.push({ name: 'run-detail'");
    expect(runsPageSource).toContain('buildRunCompanyGroupsPath');
    expect(runsPageSource).not.toContain('<Card v-if="selectedRun"');
    expect(runsPageSource).not.toContain("{{ t('runs.selectRun') }}");
    expect(runDetailPageSource).toContain('useRoute');
    expect(runDetailPageSource).toContain('loadRunDetail');
    expect(runDetailPageSource).toContain('<Card v-if="selectedRun"');
  });

  it('stacks run detail evidence, risk, and action insights vertically', () => {
    expect(runDetailPageSource).toContain('data-testid="run-detail-insight-panels" class="uno-grid uno-gap-3"');
    expect(runDetailPageSource).not.toContain('data-testid="run-detail-insight-panels" class="uno-grid uno-grid-cols-[repeat(auto-fit,minmax(210px,1fr))] uno-gap-3"');
  });

  it('keeps pinned actions above run details and moves comments plus share below the report', () => {
    const pinnedIndex = runDetailPageSource.indexOf('data-testid="run-detail-pinned-action-card"');
    const mainCardIndex = runDetailPageSource.indexOf('data-testid="run-detail-main-card"');
    const reportIndex = runDetailPageSource.indexOf('data-testid="run-detail-report-markdown"');
    const commentsIndex = runDetailPageSource.indexOf('data-testid="run-detail-comments-card"');
    const shareIndex = runDetailPageSource.indexOf('data-testid="run-detail-public-share-card"');

    expect(pinnedIndex).toBeGreaterThan(-1);
    expect(mainCardIndex).toBeGreaterThan(-1);
    expect(reportIndex).toBeGreaterThan(-1);
    expect(commentsIndex).toBeGreaterThan(-1);
    expect(shareIndex).toBeGreaterThan(-1);
    expect(pinnedIndex).toBeLessThan(mainCardIndex);
    expect(reportIndex).toBeLessThan(commentsIndex);
    expect(commentsIndex).toBeLessThan(shareIndex);
  });

  it('keeps pinned actions collapsed by default', () => {
    expect(runDetailPageSource).toContain('<details v-if="selectedRun" data-testid="run-detail-pinned-action-card"');
    expect(runDetailPageSource).not.toContain('<details v-if="selectedRun" data-testid="run-detail-pinned-action-card" open');
    expect(runDetailPageSource).not.toContain('<Card v-if="selectedRun" data-testid="run-detail-pinned-action-card"');
  });

  it('right-aligns the save pinned action button row', () => {
    expect(runDetailPageSource).toContain('class="uno-mt-3 uno-flex uno-flex-wrap uno-items-center uno-justify-end uno-gap-[0.55rem]"');
  });

  it('adds a history calendar control and record count to the run detail header', () => {
    expect(runDetailPageSource).toContain('data-testid="run-detail-history-toggle"');
    expect(runDetailPageSource).toContain('data-testid="run-detail-history-badge"');
    expect(runDetailPageSource).not.toContain('data-testid="run-detail-history-count"');
    expect(runDetailPageSource).toContain('OverlayBadge');
    expect(runDetailPageSource).toContain('DatePicker');
  });

  it('uses a sticky tab bar for run detail sections and lets report content grow with the page', () => {
    expect(runDetailPageSource).toContain('data-testid="run-detail-section-tabs"');
    expect(runDetailPageSource).toContain('uno-sticky');
    expect(runDetailPageSource).toContain('role="tablist"');
    expect(runDetailPageSource).toContain(':constrain-height="false"');
    expect(reportMarkdownSource).toContain("props.constrainHeight ? 'uno-max-h-[680px] uno-overflow-auto' : ''");
  });

  it('moves the back control into a top-left breadcrumb row near the sidebar edge', () => {
    expect(runDetailPageSource).toContain('data-testid="run-detail-breadcrumb"');
    expect(runDetailPageSource).toContain("{{ t('common.back') }}");
    expect(runDetailPageSource).toContain("{{ t('runs.runDetail') }}");
    expect(runDetailPageSource).not.toContain(":label=\"t('common.back')\"");

    const breadcrumbIndex = runDetailPageSource.indexOf('data-testid="run-detail-breadcrumb"');
    const pageHeaderIndex = runDetailPageSource.indexOf('<PageHeader');
    const actionsSlot = runDetailPageSource.split('<template #actions>')[1]?.split('</template>')[0] || '';

    expect(breadcrumbIndex).toBeGreaterThan(-1);
    expect(pageHeaderIndex).toBeGreaterThan(-1);
    expect(breadcrumbIndex).toBeLessThan(pageHeaderIndex);
    expect(actionsSlot.indexOf('data-testid="run-detail-history-badge"')).toBeLessThan(actionsSlot.indexOf(":label=\"t('common.refresh')\""));
  });

  it('formats run detail titles with company name before the ticker code in parentheses', () => {
    expect(runDetailPageSource).toContain('const runIdentityLabel = computed(() => {');
    expect(runDetailPageSource).toContain('return companyName ? `${companyName} (${ticker})` : ticker;');
    expect(runDetailPageSource).toContain(':title="selectedRun ? runHeaderTitle : t(\'runs.runDetail\')"');
    expect(runDetailPageSource).toContain('{{ runIdentityLabel }} · {{ selectedRun.date }}');
  });

  it('gives model, backend URL, and API key fields wider responsive tracks', () => {
    expect(settingsPageSource).toContain('data-testid="llm-settings-grid"');
    expect(settingsPageSource).toContain('data-testid="provider-api-key-field"');
    expect(settingsPageSource).toContain('data-testid="settings-quick-custom-model-input"');
    expect(settingsPageSource).toContain('minmax(min(100%,320px),1fr)');
  });

  it('keeps custom model id inputs available when a provider exposes only custom model ids', () => {
    expect(analyzePageSource).toContain('data-testid="analysis-quick-custom-model-input"');
    expect(analyzePageSource).toContain('data-testid="analysis-deep-custom-model-input"');
  });
});
