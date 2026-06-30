import { describe, expect, it } from 'vitest';

import { parseReportMarkdown } from './reportMarkdown';

describe('report markdown parser', () => {
  it('parses headings, strong text, lists, and paragraphs', () => {
    const blocks = parseReportMarkdown([
      '## Decision',
      '',
      '**Rating**: Buy',
      'Second sentence.',
      '',
      '- **Risk**: drawdown',
      '- Catalyst: earnings',
    ].join('\n'));

    expect(blocks).toEqual([
      {
        kind: 'heading',
        level: 2,
        content: [{ kind: 'text', text: 'Decision' }],
      },
      {
        kind: 'paragraph',
        content: [
          { kind: 'strong', text: 'Rating' },
          { kind: 'text', text: ': Buy Second sentence.' },
        ],
      },
      {
        kind: 'list',
        items: [
          [
            { kind: 'strong', text: 'Risk' },
            { kind: 'text', text: ': drawdown' },
          ],
          [{ kind: 'text', text: 'Catalyst: earnings' }],
        ],
      },
    ]);
  });

  it('parses markdown tables', () => {
    const blocks = parseReportMarkdown([
      '| Signal | Direction |',
      '| --- | --- |',
      '| Momentum | Bullish |',
      '| News | Mixed |',
    ].join('\n'));

    expect(blocks).toEqual([
      {
        kind: 'table',
        headers: ['Signal', 'Direction'],
        rows: [
          ['Momentum', 'Bullish'],
          ['News', 'Mixed'],
        ],
      },
    ]);
  });
});
