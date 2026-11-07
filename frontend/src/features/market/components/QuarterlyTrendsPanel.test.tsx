import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { marketApi } from '../api';
import type { FinancialTrendsResponse } from '../types';
import { QuarterlyTrendsPanel } from './QuarterlyTrendsPanel';

vi.mock('../api', () => ({ marketApi: { financialTrends: vi.fn() } }));

const source = {
  name: 'Synthetic source',
  url: 'https://example.org/test',
  fetched_at: '2026-01-01T00:00:00Z',
  published_at: null,
  cached: false,
  fixture: true,
};
const sample: FinancialTrendsResponse = {
  symbol: 'AAPL',
  market: 'US',
  currency: 'USD',
  mode: 'fixtures',
  frequency: 'quarterly',
  sources: [source],
  gaps: ['Synthetic figures'],
  periods: [
    {
      period_id: 'FY2025Q4',
      fiscal_year: 2025,
      fiscal_quarter: 'Q4',
      period_kind: 'standalone_quarter',
      period_start: '2025-10-01',
      period_end: '2025-12-31',
      filed_on: '2026-02-01',
      form: '10-K',
      accession: 'fixture-1',
      source,
      metrics: {
        revenue: {
          value: 1200000000,
          unit: 'USD',
          status: 'derived',
          evidence_ids: ['a', 'b'],
          calculation_id: 'calc-1',
        },
        net_income: { value: -100000, unit: 'USD', status: 'as_reported', evidence_ids: ['c'] },
      },
    },
  ],
  ttm: {
    revenue: {
      status: 'unavailable',
      value: null,
      unit: 'USD',
      reason: 'Need four quarters',
      input_period_ids: [],
    },
  },
};

beforeEach(() => {
  vi.mocked(marketApi.financialTrends).mockReset();
  vi.mocked(marketApi.financialTrends).mockResolvedValue(sample);
});

describe('quarterly financial trends panel', () => {
  it('fetches sourced quarters, distinguishes derived values and handles metric selection', async () => {
    render(<QuarterlyTrendsPanel symbol="AAPL" />);
    expect(await screen.findByText('1.2B USD')).toBeInTheDocument();
    expect(screen.getByText('Calculated from filings')).toBeInTheDocument();
    expect(screen.getByText('Need four quarters')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Net income' }));
    expect(screen.getByText('-100,000 USD')).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Data coverage and calculation limitations/));
    expect(screen.getByText('Synthetic figures')).toBeInTheDocument();
    expect(marketApi.financialTrends).toHaveBeenCalledWith('AAPL');
  });
  it('displays unsupported Canadian coverage without invented figures', async () => {
    vi.mocked(marketApi.financialTrends).mockResolvedValue({
      ...sample,
      symbol: 'RY.TO',
      market: 'CA',
      currency: 'CAD',
      mode: 'live',
      periods: [],
      sources: [],
      ttm: {},
      gaps: ['Canadian financials unavailable'],
    });
    render(<QuarterlyTrendsPanel symbol="RY.TO" />);
    expect(
      await screen.findByText('No comparable quarterly observations are available for this metric.'),
    ).toBeInTheDocument();
    expect(screen.queryByText('1.2B USD')).toBeNull();
  });
  it('retries provider errors without falling back to synthetic values', async () => {
    vi.mocked(marketApi.financialTrends).mockRejectedValueOnce(new Error('SEC unavailable'));
    render(<QuarterlyTrendsPanel symbol="AAPL" />);
    expect(await screen.findByText('SEC unavailable')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    await waitFor(() => expect(screen.getByText('1.2B USD')).toBeInTheDocument());
  });
  it('re-fetches on ticker change without showing the prior ticker result', async () => {
    const view = render(<QuarterlyTrendsPanel key="AAPL" symbol="AAPL" />);
    await screen.findByText('1.2B USD');
    vi.mocked(marketApi.financialTrends).mockResolvedValue({ ...sample, symbol: 'NVDA', periods: [] });
    view.rerender(<QuarterlyTrendsPanel key="NVDA" symbol="NVDA" />);
    expect(
      await screen.findByText('No comparable quarterly observations are available for this metric.'),
    ).toBeInTheDocument();
    expect(marketApi.financialTrends).toHaveBeenLastCalledWith('NVDA');
  });
});
