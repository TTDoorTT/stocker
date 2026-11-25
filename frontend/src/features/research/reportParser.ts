export type InlineToken =
  | { type: 'text'; text: string }
  | { type: 'bold'; text: string }
  | { type: 'code'; text: string }
  | { type: 'ref'; refId: string }
  | { type: 'link'; label: string; href: string };

export type ReportBlock =
  | { type: 'heading3'; text: string }
  | { type: 'blockquote'; lines: string[] }
  | { type: 'list'; items: string[] }
  | { type: 'table'; headers: string[]; rows: string[][] }
  | { type: 'paragraph'; text: string };

export interface ReportSection {
  id: string;
  title: string;
  blocks: ReportBlock[];
}

export interface ParsedReport {
  title: string;
  metadata: Array<{ label: string; value: string }>;
  notices: string[];
  sections: ReportSection[];
}

const REF_ID_PATTERN = /^(?:ev|calc)-[a-z0-9-]+$/i;

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function splitTableRow(line: string): string[] {
  const trimmed = line.trim().replace(/^\|/, '').replace(/\|$/, '');
  const cells: string[] = [];
  let current = '';
  for (let i = 0; i < trimmed.length; i += 1) {
    if (trimmed[i] === '\\' && trimmed[i + 1] === '|') {
      current += '|';
      i += 1;
    } else if (trimmed[i] === '|') {
      cells.push(current.trim());
      current = '';
    } else {
      current += trimmed[i];
    }
  }
  cells.push(current.trim());
  return cells;
}

function isTableSeparator(line: string): boolean {
  const trimmed = line.trim();
  if (!trimmed.startsWith('|') || !trimmed.endsWith('|')) return false;
  const cells = splitTableRow(trimmed);
  return cells.length > 0 && cells.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function stripMarkdownWrapper(text: string): string {
  return text
    .replace(/^\*\*(.*)\*\*$/, '$1')
    .replace(/^`(.*)`$/, '$1')
    .trim();
}

export function extractRowRefId(cells: string[], sectionTitle: string): string | null {
  const lower = sectionTitle.toLowerCase();
  if (lower.includes('sources')) {
    const first = stripMarkdownWrapper(cells[0] ?? '');
    if (REF_ID_PATTERN.test(first)) return first;
  }
  if (lower.includes('deterministic calculations')) {
    const refsCell = cells[3] ?? '';
    const match = refsCell.match(/\b(calc-[a-z0-9-]+)\b/i);
    if (match) return match[1];
  }
  return null;
}

export function parseBlocks(lines: string[]): ReportBlock[] {
  const blocks: ReportBlock[] = [];
  let i = 0;

  while (i < lines.length) {
    const raw = lines[i];
    const trimmed = raw.trim();

    if (!trimmed) {
      i += 1;
      continue;
    }

    if (trimmed.startsWith('### ')) {
      blocks.push({ type: 'heading3', text: trimmed.slice(4).trim() });
      i += 1;
      continue;
    }

    if (trimmed.startsWith('> ')) {
      const quoteLines: string[] = [];
      while (i < lines.length && lines[i].trim().startsWith('> ')) {
        quoteLines.push(lines[i].trim().slice(2).trim());
        i += 1;
      }
      blocks.push({ type: 'blockquote', lines: quoteLines });
      continue;
    }

    if (trimmed.startsWith('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1])) {
      const headers = splitTableRow(trimmed);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        rows.push(splitTableRow(lines[i]));
        i += 1;
      }
      blocks.push({ type: 'table', headers, rows });
      continue;
    }

    if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      const items: string[] = [];
      while (i < lines.length) {
        const current = lines[i].trim();
        if (current.startsWith('- ') || current.startsWith('* ')) {
          items.push(current.slice(2).trim());
          i += 1;
        } else {
          break;
        }
      }
      blocks.push({ type: 'list', items });
      continue;
    }

    const paragraphLines: string[] = [];
    while (i < lines.length) {
      const current = lines[i].trim();
      if (
        !current ||
        current.startsWith('### ') ||
        current.startsWith('> ') ||
        current.startsWith('- ') ||
        current.startsWith('* ') ||
        (current.startsWith('|') && i + 1 < lines.length && isTableSeparator(lines[i + 1]))
      ) {
        break;
      }
      paragraphLines.push(current);
      i += 1;
    }
    if (paragraphLines.length) {
      blocks.push({ type: 'paragraph', text: paragraphLines.join(' ') });
    }
  }

  return blocks;
}

export function parseReportMarkdown(markdown: string): ParsedReport {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n');
  let title = 'Research Brief';
  const preambleLines: string[] = [];
  const sections: ReportSection[] = [];
  let currentSection: { title: string; lines: string[] } | null = null;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!currentSection && trimmed.startsWith('# ')) {
      title = trimmed.slice(2).trim();
      continue;
    }
    if (trimmed.startsWith('## ')) {
      if (currentSection) {
        sections.push({
          id: `section-${slugify(currentSection.title)}`,
          title: currentSection.title,
          blocks: parseBlocks(currentSection.lines),
        });
      }
      currentSection = { title: trimmed.slice(3).trim(), lines: [] };
      continue;
    }
    if (currentSection) {
      currentSection.lines.push(line);
    } else {
      preambleLines.push(line);
    }
  }

  if (currentSection) {
    sections.push({
      id: `section-${slugify(currentSection.title)}`,
      title: currentSection.title,
      blocks: parseBlocks(currentSection.lines),
    });
  }

  const preambleBlocks = parseBlocks(preambleLines);
  const metadata: Array<{ label: string; value: string }> = [];
  const notices: string[] = [];

  for (const block of preambleBlocks) {
    if (block.type === 'table' && block.headers.length === 2 && block.headers[0].toLowerCase() === 'field') {
      for (const row of block.rows) {
        if (row.length >= 2) {
          metadata.push({
            label: stripMarkdownWrapper(row[0]),
            value: stripMarkdownWrapper(row[1]),
          });
        }
      }
    } else if (block.type === 'blockquote') {
      notices.push(block.lines.join(' '));
    }
  }

  return { title, metadata, notices, sections };
}

function expandCodeToken(codeContent: string, allowRefButtons: boolean): InlineToken[] {
  if (!allowRefButtons) {
    return [{ type: 'code', text: codeContent }];
  }
  const parts = codeContent
    .split(',')
    .map((part) => part.trim())
    .filter(Boolean);
  if (parts.length > 0 && parts.every((part) => REF_ID_PATTERN.test(part))) {
    const tokens: InlineToken[] = [];
    parts.forEach((part, idx) => {
      if (idx > 0) tokens.push({ type: 'text', text: ' ' });
      tokens.push({ type: 'ref', refId: part });
    });
    return tokens;
  }
  return [{ type: 'code', text: codeContent }];
}

export function parseInlineTokens(text: string, options: { allowRefButtons?: boolean } = {}): InlineToken[] {
  const allowRefButtons = options.allowRefButtons ?? true;
  const tokens: InlineToken[] = [];
  const pattern = /\[([^\]]+)\]\(([^)]+)\)|\*\*([^*]+)\*\*|`([^`]+)`/g;
  let lastIndex = 0;

  for (const match of text.matchAll(pattern)) {
    const index = match.index ?? 0;
    if (index > lastIndex) {
      tokens.push({ type: 'text', text: text.slice(lastIndex, index) });
    }

    if (match[1] !== undefined && match[2] !== undefined) {
      const label = match[1];
      const href = match[2];
      if (href.startsWith('#ref-')) {
        const refId = href.slice('#ref-'.length);
        if (allowRefButtons && REF_ID_PATTERN.test(refId)) {
          tokens.push({ type: 'ref', refId });
        } else {
          tokens.push({ type: 'code', text: label });
        }
      } else if (href.startsWith('https://')) {
        tokens.push({ type: 'link', label, href });
      } else {
        tokens.push({ type: 'text', text: label });
      }
    } else if (match[3] !== undefined) {
      tokens.push({ type: 'bold', text: match[3] });
    } else if (match[4] !== undefined) {
      tokens.push(...expandCodeToken(match[4], allowRefButtons));
    }

    lastIndex = index + match[0].length;
  }

  if (lastIndex < text.length) {
    tokens.push({ type: 'text', text: text.slice(lastIndex) });
  }

  return tokens;
}
