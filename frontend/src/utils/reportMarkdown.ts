export type ReportInline = {
  kind: 'text' | 'strong';
  text: string;
};

export type ReportBlock =
  | { kind: 'heading'; level: number; content: ReportInline[] }
  | { kind: 'paragraph'; content: ReportInline[] }
  | { kind: 'list'; items: ReportInline[][] }
  | { kind: 'table'; headers: string[]; rows: string[][] }
  | { kind: 'code'; text: string };

function parseInline(text: string): ReportInline[] {
  const segments: ReportInline[] = [];
  let remaining = text;

  while (remaining.length > 0) {
    const start = remaining.indexOf('**');
    if (start < 0) {
      segments.push({ kind: 'text', text: remaining });
      break;
    }

    if (start > 0) {
      segments.push({ kind: 'text', text: remaining.slice(0, start) });
    }

    const afterStart = remaining.slice(start + 2);
    const end = afterStart.indexOf('**');
    if (end < 0) {
      segments.push({ kind: 'text', text: remaining.slice(start) });
      break;
    }

    const strongText = afterStart.slice(0, end);
    if (strongText) {
      segments.push({ kind: 'strong', text: strongText });
    }
    remaining = afterStart.slice(end + 2);
  }

  return segments.filter((segment) => segment.text.length > 0);
}

function isTableSeparator(line: string): boolean {
  const cells = splitTableRow(line);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell.trim()));
}

function splitTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim());
}

function isTableStart(lines: string[], index: number): boolean {
  return Boolean(
    lines[index]?.includes('|')
    && lines[index + 1]?.includes('|')
    && isTableSeparator(lines[index + 1]),
  );
}

function isListItem(line: string): boolean {
  return /^\s*[-*]\s+\S/.test(line);
}

function isHeading(line: string): boolean {
  return /^#{1,4}\s+\S/.test(line);
}

function isBlockStart(lines: string[], index: number): boolean {
  const line = lines[index] || '';
  return line.trim() === ''
    || line.trim().startsWith('```')
    || isHeading(line)
    || isListItem(line)
    || isTableStart(lines, index);
}

export function parseReportMarkdown(source: string): ReportBlock[] {
  const lines = source.replace(/\r\n/g, '\n').split('\n');
  const blocks: ReportBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index];
    const trimmed = line.trim();

    if (!trimmed) {
      index += 1;
      continue;
    }

    if (trimmed.startsWith('```')) {
      const codeLines: string[] = [];
      index += 1;
      while (index < lines.length && !lines[index].trim().startsWith('```')) {
        codeLines.push(lines[index]);
        index += 1;
      }
      if (index < lines.length) {
        index += 1;
      }
      blocks.push({ kind: 'code', text: codeLines.join('\n') });
      continue;
    }

    const headingMatch = trimmed.match(/^(#{1,4})\s+(.+)$/);
    if (headingMatch) {
      blocks.push({
        kind: 'heading',
        level: headingMatch[1].length,
        content: parseInline(headingMatch[2].trim()),
      });
      index += 1;
      continue;
    }

    if (isTableStart(lines, index)) {
      const headers = splitTableRow(lines[index]);
      const rows: string[][] = [];
      index += 2;
      while (index < lines.length && lines[index].includes('|') && lines[index].trim()) {
        rows.push(splitTableRow(lines[index]));
        index += 1;
      }
      blocks.push({ kind: 'table', headers, rows });
      continue;
    }

    if (isListItem(line)) {
      const items: ReportInline[][] = [];
      while (index < lines.length && isListItem(lines[index])) {
        items.push(parseInline(lines[index].replace(/^\s*[-*]\s+/, '').trim()));
        index += 1;
      }
      blocks.push({ kind: 'list', items });
      continue;
    }

    const paragraphLines = [trimmed];
    index += 1;
    while (index < lines.length && !isBlockStart(lines, index)) {
      paragraphLines.push(lines[index].trim());
      index += 1;
    }
    blocks.push({ kind: 'paragraph', content: parseInline(paragraphLines.join(' ')) });
  }

  return blocks;
}
