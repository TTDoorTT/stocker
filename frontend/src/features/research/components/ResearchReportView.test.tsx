import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ResearchReportView } from './ResearchReportView';

const SAMPLE_REPORT = `# AAPL — Research Brief

| Field | Value |
|---|---|
| **Symbol** | \`AAPL\` (US) |
| **Mode** | \`live\` |
| **Status** | \`incomplete\` |

> Educational research only — not investment advice.

## Executive summary

> **Bottom line:** Apple shows **accelerating revenue growth** with **unbenchmarked valuation**.

- **15.06%** — Revenue expanded in the latest fiscal year. ([calc-rev123](#ref-calc-rev123))
- Company identity is verified across sources. (\`ev-id111, ev-id222\`)

### Key metrics snapshot

| Metric | Value | Reference |
|---|---|---|
| Revenue YoY Growth | **15.06%** | [calc-rev123](#ref-calc-rev123) |
| Net Profit Margin | **27.60%** | [calc-pm456](#ref-calc-pm456) |

## Deterministic calculations

| Metric | Value | Unit | References |
|---|---|---|---|
| Revenue YoY Growth | 15.06% | % | \`calc-rev123\`; [ev-id111](#ref-ev-id111) |
| Net Profit Margin | 27.60% | % | \`calc-pm456\`; [ev-id222](#ref-ev-id222) |

## Data gaps

- No licensed analyst consensus is captured.

## Sources and timestamps

| Evidence ID | Field | Period | Source | Published | Fetched |
|---|---|---|---|---|---|
| \`ev-id111\` | revenue | 2024..2025 | [SEC EDGAR](https://www.sec.gov/example) | 2025-11-01 | \`2025-11-02T00:00:00Z\` |
| \`ev-id222\` | company_name | current | [Finnhub](https://finnhub.io/docs/api/company-profile2) | Unavailable | \`2025-11-02T00:00:00Z\` |
`;

describe('ResearchReportView', () => {
  it('renders KPI snapshot cards, bold highlights, and collapsible audit tables', () => {
    render(<ResearchReportView markdown={SAMPLE_REPORT} />);

    expect(screen.getByRole('heading', { name: 'AAPL — Research Brief' })).toBeInTheDocument();
    expect(screen.getByText('accelerating revenue growth')).toHaveClass('report-highlight-text');
    expect(screen.getByLabelText('Key metrics snapshot')).toBeInTheDocument();
    expect(screen.getByText('Revenue YoY Growth')).toBeInTheDocument();
    expect(screen.getByText('27.60%')).toBeInTheDocument();

    // Audit tables and Data gaps start collapsed so the main brief stays compact and scannable.
    expect(screen.queryByText('SEC EDGAR ↗')).not.toBeInTheDocument();
    expect(screen.queryByText('No licensed analyst consensus is captured.')).not.toBeInTheDocument();

    const dataGapsToggle = screen.getByRole('button', { name: /Data gaps 1 note/i });
    expect(dataGapsToggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(dataGapsToggle);
    expect(dataGapsToggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText('No licensed analyst consensus is captured.')).toBeInTheDocument();
  });

  it('expands calculations and highlights the matching row when clicking a calc ref chip', () => {
    const scrollIntoView = vi.fn();
    Element.prototype.scrollIntoView = scrollIntoView;

    const { container } = render(<ResearchReportView markdown={SAMPLE_REPORT} />);

    const calcChips = screen.getAllByRole('button', { name: 'calc-rev123' });
    fireEvent.click(calcChips[0]);

    const highlightedRow = container.querySelector('tr[data-ref-row="calc-rev123"]');
    expect(highlightedRow).not.toBeNull();
    expect(highlightedRow).toHaveClass('report-row-highlighted');
    expect(screen.getByText('Selected evidence')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '← Back to claim' })).toBeInTheDocument();

    // Clicking an evidence chip inside the calculation row jumps to Sources and highlights that evidence row.
    const evChipInsideCalc = within(highlightedRow as HTMLElement).getByRole('button', {
      name: 'ev-id111',
    });
    fireEvent.click(evChipInsideCalc);

    const highlightedEvRow = container.querySelector('tr[data-ref-row="ev-id111"]');
    expect(highlightedEvRow).not.toBeNull();
    expect(highlightedEvRow).toHaveClass('report-row-highlighted');
    expect(screen.getByRole('link', { name: 'SEC EDGAR ↗' })).toHaveAttribute(
      'href',
      'https://www.sec.gov/example',
    );
  });

  it('supports legacy comma-separated code evidence references and dismisses selection', () => {
    const { container } = render(<ResearchReportView markdown={SAMPLE_REPORT} />);

    fireEvent.click(screen.getByRole('button', { name: 'ev-id222' }));
    const row = container.querySelector('tr[data-ref-row="ev-id222"]');
    expect(row).toHaveClass('report-row-highlighted');

    fireEvent.click(screen.getByRole('button', { name: 'Dismiss' }));
    expect(row).not.toHaveClass('report-row-highlighted');
  });
});
