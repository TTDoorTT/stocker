import { describe, expect, it } from 'vitest';
import { chartGeometry, formatFinancial, quarterSeries } from './quarterlyMath';
import type { FinancialPeriod } from './types';

const source = {
  name: 'SEC',
  url: 'https://data.sec.gov/',
  fetched_at: '2026-10-01T00:00:00Z',
  published_at: null,
  cached: false,
  fixture: false,
};
const periods: FinancialPeriod[] = [
  {
    period_id: 'FY2026Q2',
    fiscal_year: 2026,
    fiscal_quarter: 'Q2',
    period_kind: 'standalone_quarter',
    period_start: '2026-04-01',
    period_end: '2026-06-30',
    filed_on: '2026-07-31',
    form: '10-Q',
    accession: 'one',
    source,
    metrics: { revenue: { value: -50, unit: 'USD', status: 'as_reported', evidence_ids: ['a'] } },
  },
  {
    period_id: 'FY2026Q1',
    fiscal_year: 2026,
    fiscal_quarter: 'Q1',
    period_kind: 'standalone_quarter',
    period_start: '2026-01-01',
    period_end: '2026-03-31',
    filed_on: '2026-04-30',
    form: '10-Q',
    accession: 'two',
    source,
    metrics: {
      revenue: { value: 0, unit: 'USD', status: 'derived', evidence_ids: ['b'], calculation_id: 'calc-b' },
    },
  },
  {
    period_id: 'FY2025Q4',
    fiscal_year: 2025,
    fiscal_quarter: 'Q4',
    period_kind: 'standalone_quarter',
    period_start: '2025-10-01',
    period_end: '2025-12-31',
    filed_on: '2026-02-15',
    form: '10-K',
    accession: 'three',
    source,
    metrics: {},
  },
];

describe('quarterly presentation math', () => {
  it('sorts quarter periods and keeps zero distinct from unavailable', () => {
    const rows = quarterSeries(periods, 'revenue');
    expect(rows.map((r) => r.id)).toEqual(['FY2025Q4', 'FY2026Q1', 'FY2026Q2']);
    expect(rows.map((r) => r.value)).toEqual([null, 0, -50]);
  });
  it('supports negative values with a zero baseline', () => {
    const g = chartGeometry([-50, 0, 100]);
    expect(g).not.toBeNull();
    expect(g!.y(100)).toBeLessThan(g!.baseline);
    expect(g!.y(-50)).toBeGreaterThan(g!.baseline);
  });
  it('does not fabricate an axis when there are no observations', () => {
    expect(chartGeometry([null, null])).toBeNull();
  });
  it('formats EPS and large currency amounts without dropping zero', () => {
    expect(formatFinancial(0, 'revenue', 'USD')).toContain('0');
    expect(formatFinancial(1500000000, 'revenue', 'USD')).toContain('B USD');
    expect(formatFinancial(1.235, 'diluted_eps', 'USD')).toBe('1.24 USD/share');
    expect(formatFinancial(null, 'revenue', 'USD')).toBe('Unavailable');
  });
});
