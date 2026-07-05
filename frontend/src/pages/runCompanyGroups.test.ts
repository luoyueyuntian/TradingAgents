import { describe, expect, it } from 'vitest';

import { buildRunCompanyGroupsPath } from './runCompanyGroups';

describe('run company groups helpers', () => {
  it('builds a paginated company-group API path', () => {
    expect(buildRunCompanyGroupsPath({
      q: 'apple',
      status: 'completed',
      archived: 'active',
      page: 2,
      pageSize: 10,
    })).toBe('/api/runs/company-groups?q=apple&status=completed&archived=active&page=2&page_size=10');
  });
});
