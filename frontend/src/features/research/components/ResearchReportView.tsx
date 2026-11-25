import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import {
  extractRowRefId,
  parseInlineTokens,
  parseReportMarkdown,
  type ReportBlock,
  type ReportSection,
} from '../reportParser';

interface ResearchReportViewProps {
  markdown: string;
}

const COLLAPSIBLE_SECTIONS = new Set(['data gaps', 'deterministic calculations', 'sources and timestamps']);

function isCollapsibleSection(title: string): boolean {
  return COLLAPSIBLE_SECTIONS.has(title.toLowerCase());
}

function collapsibleItemCount(section: ReportSection): { count: number; unit: string } {
  const lower = section.title.toLowerCase();
  if (lower === 'data gaps') {
    const count = section.blocks.reduce(
      (sum, block) => sum + (block.type === 'list' ? block.items.length : 0),
      0,
    );
    return { count, unit: count === 1 ? 'note' : 'notes' };
  }
  const tableBlock = section.blocks.find((b) => b.type === 'table');
  const count = tableBlock && tableBlock.type === 'table' ? tableBlock.rows.length : 0;
  return { count, unit: lower.includes('calculations') ? 'metrics' : 'records' };
}

function shortJumpLabel(title: string): string {
  const lower = title.toLowerCase();
  if (lower === 'executive summary') return 'Summary';
  if (lower === 'company profile') return 'Profile';
  if (lower === 'financial performance') return 'Financials';
  if (lower === 'risks and counterevidence') return 'Risks';
  if (lower === 'deterministic calculations') return 'Calculations';
  if (lower === 'sources and timestamps') return 'Sources';
  return title;
}

function isKpiSnapshotTable(prevBlock: ReportBlock | undefined, block: ReportBlock): boolean {
  return (
    prevBlock?.type === 'heading3' &&
    prevBlock.text.toLowerCase() === 'key metrics snapshot' &&
    block.type === 'table' &&
    block.headers.length === 3 &&
    block.headers[0].toLowerCase() === 'metric'
  );
}

function escapeSelector(value: string): string {
  if (typeof CSS !== 'undefined' && typeof CSS.escape === 'function') {
    return CSS.escape(value);
  }
  return value.replace(/[^a-zA-Z0-9_-]/g, '\\$&');
}

export function ResearchReportView({ markdown }: ResearchReportViewProps) {
  const parsed = useMemo(() => parseReportMarkdown(markdown), [markdown]);
  const rootRef = useRef<HTMLDivElement>(null);
  const returnElementRef = useRef<HTMLElement | null>(null);
  const [selectedRef, setSelectedRef] = useState<string | null>(null);
  const [highlightPulse, setHighlightPulse] = useState(0);
  const [expandedAudit, setExpandedAudit] = useState<Record<string, boolean>>({});

  useEffect(() => {
    setSelectedRef(null);
    setExpandedAudit({});
    returnElementRef.current = null;
  }, [markdown]);

  useEffect(() => {
    if (!selectedRef) return;
    const frame = requestAnimationFrame(() => {
      const container = rootRef.current;
      if (!container) return;
      const target = container.querySelector<HTMLElement>(`[data-ref-row="${escapeSelector(selectedRef)}"]`);
      if (target) {
        target.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
      }
    });
    return () => cancelAnimationFrame(frame);
  }, [selectedRef, highlightPulse, expandedAudit]);

  function jumpToRef(refId: string, originElement: HTMLElement | null) {
    returnElementRef.current = originElement;
    const isCalc = refId.toLowerCase().startsWith('calc-');
    const targetSectionKey = isCalc ? 'deterministic calculations' : 'sources and timestamps';
    setExpandedAudit((prev) => ({ ...prev, [targetSectionKey]: true }));
    setSelectedRef(refId);
    setHighlightPulse((value) => value + 1);
  }

  function jumpBackToOrigin() {
    const origin = returnElementRef.current;
    if (origin && origin.isConnected) {
      origin.scrollIntoView?.({ behavior: 'smooth', block: 'center' });
      origin.focus?.();
    }
    setSelectedRef(null);
  }

  function jumpToSection(section: ReportSection) {
    const lower = section.title.toLowerCase();
    if (isCollapsibleSection(section.title)) {
      setExpandedAudit((prev) => ({ ...prev, [lower]: true }));
    }
    requestAnimationFrame(() => {
      const target = rootRef.current?.querySelector<HTMLElement>(`#${escapeSelector(section.id)}`);
      target?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
    });
  }

  function renderInline(text: string, allowRefButtons = true, excludeRefId?: string | null) {
    const tokens = parseInlineTokens(text, { allowRefButtons });
    return tokens.map((token, idx) => {
      if (token.type === 'text') return <Fragment key={idx}>{token.text}</Fragment>;
      if (token.type === 'bold') {
        return (
          <strong key={idx} className="report-highlight-text">
            {token.text}
          </strong>
        );
      }
      if (token.type === 'code') {
        return <code key={idx}>{token.text}</code>;
      }
      if (token.type === 'link') {
        return (
          <a key={idx} href={token.href} target="_blank" rel="noreferrer noopener">
            {token.label} ↗
          </a>
        );
      }
      if (excludeRefId && token.refId === excludeRefId) {
        return <code key={idx}>{token.refId}</code>;
      }
      const isCalc = token.refId.toLowerCase().startsWith('calc-');
      const isActive = selectedRef === token.refId;
      return (
        <button
          key={idx}
          type="button"
          className={`ref-chip ${isCalc ? 'ref-chip-calc' : 'ref-chip-ev'}${isActive ? ' active' : ''}`}
          data-ref-target={token.refId}
          title={isCalc ? `Jump to calculation ${token.refId}` : `Jump to source evidence ${token.refId}`}
          onClick={(event) => jumpToRef(token.refId, event.currentTarget)}
        >
          {token.refId}
        </button>
      );
    });
  }

  function renderBlock(block: ReportBlock, idx: number, section: ReportSection) {
    const prevBlock = idx > 0 ? section.blocks[idx - 1] : undefined;

    if (block.type === 'heading3') {
      return (
        <h3 key={idx} className="report-subheading">
          {block.text}
        </h3>
      );
    }

    if (block.type === 'blockquote') {
      return (
        <div key={idx} className="report-callout">
          {block.lines.map((line, lineIdx) => (
            <p key={lineIdx}>{renderInline(line)}</p>
          ))}
        </div>
      );
    }

    if (block.type === 'paragraph') {
      return (
        <p key={idx} className="report-paragraph">
          {renderInline(block.text)}
        </p>
      );
    }

    if (block.type === 'list') {
      const isDataGaps = section.title.toLowerCase() === 'data gaps';
      const isRiskList =
        prevBlock?.type === 'heading3' &&
        ['counterevidence', 'invalidation conditions', 'valuation limitations'].includes(
          prevBlock.text.toLowerCase(),
        );
      return (
        <ul
          key={idx}
          className={`report-list${isDataGaps ? ' report-gap-list' : ''}${isRiskList ? ' report-caution-list' : ''}`}
        >
          {block.items.map((item, itemIdx) => (
            <li key={itemIdx}>{renderInline(item)}</li>
          ))}
        </ul>
      );
    }

    if (isKpiSnapshotTable(prevBlock, block)) {
      return (
        <div key={idx} className="report-kpi-grid" aria-label="Key metrics snapshot">
          {block.rows.map((row, rowIdx) => (
            <div key={rowIdx} className="report-kpi-card">
              <span className="report-kpi-label">{renderInline(row[0] ?? '', false)}</span>
              <div className="report-kpi-value">{renderInline(row[1] ?? '', false)}</div>
              <div className="report-kpi-ref">{renderInline(row[2] ?? '', true)}</div>
            </div>
          ))}
        </div>
      );
    }

    const isSourcesTable = section.title.toLowerCase().includes('sources');
    const isCalcsTable = section.title.toLowerCase().includes('deterministic calculations');

    return (
      <div key={idx} className="table-scroll report-table-wrap">
        <table className="report-table">
          <thead>
            <tr>
              {block.headers.map((header, hIdx) => (
                <th key={hIdx}>{header}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {block.rows.map((row, rIdx) => {
              const rowRefId = extractRowRefId(row, section.title);
              const isSelected = Boolean(rowRefId && selectedRef === rowRefId);
              return (
                <tr
                  key={rIdx}
                  id={rowRefId ? `ref-${rowRefId}` : undefined}
                  data-ref-row={rowRefId ?? undefined}
                  className={isSelected ? 'report-row-highlighted' : undefined}
                >
                  {row.map((cell, cIdx) => {
                    const allowButtons = isSourcesTable ? cIdx > 0 : isCalcsTable ? cIdx === 3 : true;
                    return (
                      <td key={cIdx}>
                        {renderInline(cell, allowButtons, rowRefId)}
                        {isSelected && cIdx === 0 && (
                          <div className="report-row-selected-bar">
                            <span className="report-selected-pill">Selected evidence</span>
                            {returnElementRef.current && (
                              <button type="button" className="report-back-btn" onClick={jumpBackToOrigin}>
                                ← Back to claim
                              </button>
                            )}
                            <button
                              type="button"
                              className="report-clear-btn"
                              onClick={() => setSelectedRef(null)}
                            >
                              Dismiss
                            </button>
                          </div>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div ref={rootRef} className="report-view">
      <div className="report-header">
        <h1 className="report-title">{parsed.title}</h1>
        {parsed.metadata.length > 0 && (
          <div className="report-meta-strip">
            {parsed.metadata.map((item) => (
              <span key={item.label} className="report-meta-pill">
                <span className="report-meta-key">{item.label}</span>
                <strong>{item.value}</strong>
              </span>
            ))}
          </div>
        )}
        {parsed.notices.map((notice, idx) => (
          <p
            key={idx}
            className={`report-disclaimer${notice.toUpperCase().includes('SYNTHETIC') ? ' synthetic' : ''}`}
          >
            {renderInline(notice, false)}
          </p>
        ))}
      </div>

      {parsed.sections.length > 1 && (
        <nav className="report-jump-bar" aria-label="Report sections">
          {parsed.sections.map((section) => (
            <button
              key={section.id}
              type="button"
              className={`report-jump-pill${isCollapsibleSection(section.title) ? ' audit' : ''}`}
              onClick={() => jumpToSection(section)}
            >
              {shortJumpLabel(section.title)}
            </button>
          ))}
        </nav>
      )}

      <div className="report-sections">
        {parsed.sections.map((section) => {
          const lower = section.title.toLowerCase();
          if (isCollapsibleSection(section.title)) {
            const { count, unit } = collapsibleItemCount(section);
            const isOpen = Boolean(expandedAudit[lower]);
            const isGaps = lower === 'data gaps';
            return (
              <section key={section.id} id={section.id} className="report-audit-section">
                <button
                  type="button"
                  className="report-audit-toggle"
                  aria-expanded={isOpen}
                  onClick={() => setExpandedAudit((prev) => ({ ...prev, [lower]: !prev[lower] }))}
                >
                  <span>
                    <strong>{section.title}</strong>
                    <span className="report-audit-count">
                      {count} {unit}
                    </span>
                  </span>
                  <span className="report-audit-hint">
                    {isOpen
                      ? isGaps
                        ? 'Hide ▴'
                        : 'Hide table ▴'
                      : isGaps
                        ? 'Expand ▾'
                        : 'Expand table or click any ref chip ▾'}
                  </span>
                </button>
                {isOpen && (
                  <div className="report-audit-body">
                    {section.blocks.map((block, idx) => renderBlock(block, idx, section))}
                  </div>
                )}
              </section>
            );
          }

          return (
            <section
              key={section.id}
              id={section.id}
              className={`report-section${lower === 'executive summary' ? ' report-section-exec' : ''}`}
            >
              <h2 className="report-section-title">{section.title}</h2>
              {section.blocks.map((block, idx) => renderBlock(block, idx, section))}
            </section>
          );
        })}
      </div>
    </div>
  );
}
