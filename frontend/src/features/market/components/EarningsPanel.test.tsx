import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { marketApi } from '../api';
import type { EarningsResponse } from '../types';
import { EarningsPanel } from './EarningsPanel';

vi.mock('../api', () => ({ marketApi: { earnings: vi.fn() } }));

const source = {
  name: 'Synthetic vendor calendar',
  url: 'https://example.org/synthetic',
  fetched_at: '2026-11-07T20:00:00Z',
  published_at: null,
  cached: false,
  fixture: true,
};

const sample: EarningsResponse = {
  symbol: 'AAPL',
  market: 'US',
  currency: 'USD',
  mode: 'fixtures',
  upcoming: {
    scheduled_date: '2026-12-05',
    date_status: 'estimated',
    timing: 'unknown',
    fiscal_year: 2026,
    fiscal_quarter: 'Q2',
    eps_estimate: 1.4,
    eps_estimate_basis: 'adjusted',
    revenue_estimate: 1_400_000_000,
    source,
  },
  history: [
    {
      event_id: 'US:AAPL:earnings_release:FY2026Q1',
      fiscal_year: 2026,
      fiscal_quarter: 'Q1',
      reported_on: '2026-09-01',
      actual_eps: 1.25,
      actual_basis: 'adjusted',
      estimate_eps: 1.2,
      estimate_basis: 'adjusted',
      surprise_pct: 4.1666667,
      actual_revenue: 1_250_000_000,
      estimate_revenue: 1_200_000_000,
      revenue_surprise_pct: 4.1666667,
      source,
    },
  ],
  sources: [source],
  gaps: ['SYNTHETIC values are not real financial evidence.'],
};

beforeEach(() => {
  vi.mocked(marketApi.earnings).mockReset();
  vi.mocked(marketApi.earnings).mockResolvedValue(sample);
});

describe('earnings preview and review', () => {
  it('loads a scoped symbol and labels upcoming dates as vendor-estimated', async () => {
    render(<EarningsPanel symbol="AAPL" />);
    expect(await screen.findByText('Dec 5, 2026')).toBeInTheDocument();
    expect(marketApi.earnings).toHaveBeenCalledWith('AAPL');
    expect(screen.getByText(/Upcoming earnings · Vendor estimate/)).toBeInTheDocument();
    expect(screen.getByText(/Release time unverified/)).toBeInTheDocument();
    expect(screen.getByText('Demo · synthetic fixtures')).toBeInTheDocument();
    expect(screen.getByText('$1.40B')).toBeInTheDocument();
    expect(screen.getAllByText('Vendor adjusted / non-GAAP').length).toBeGreaterThan(0);
  });

  it('shows both actual and estimate fields with backend-computed surprise', async () => {
    render(<EarningsPanel symbol="AAPL" />);
    const table = await screen.findByRole('table');
    expect(within(table).getByText('Sep 1, 2026')).toBeInTheDocument();
    expect(within(table).getByText('Q1 FY2026')).toBeInTheDocument();
    expect(within(table).getByText('$1.25')).toBeInTheDocument();
    expect(within(table).getByText('$1.20')).toBeInTheDocument();
    expect(within(table).getByText('$1.25B')).toBeInTheDocument();
    expect(within(table).getByText('$1.20B')).toBeInTheDocument();
    expect(within(table).getAllByText('+4.17%')).toHaveLength(2);
    fireEvent.click(screen.getByText(/Coverage and interpretation limits/));
    expect(screen.getByText(/not real financial evidence/)).toBeInTheDocument();
  });

  it('handles absent future dates, EPS, and historical coverage without invented results', async () => {
    vi.mocked(marketApi.earnings).mockResolvedValue({
      ...sample,
      upcoming: null,
      history: [],
      sources: [],
      gaps: ['No calendar entitlement'],
    });
    render(<EarningsPanel symbol="AAPL" />);
    expect(await screen.findByText('No upcoming earnings date available')).toBeInTheDocument();
    expect(screen.getByText(/No dated earnings results returned/)).toBeInTheDocument();
    expect(screen.queryByRole('table')).toBeNull();
  });

  it('shows unsupported Canadian coverage without implying a Canadian release', async () => {
    vi.mocked(marketApi.earnings).mockResolvedValue({
      symbol: 'RY.TO',
      market: 'CA',
      currency: 'CAD',
      mode: 'live',
      upcoming: null,
      history: [],
      sources: [],
      gaps: ['Canadian earnings coverage is unavailable'],
    });
    render(<EarningsPanel symbol="RY.TO" />);
    expect(await screen.findByText('No upcoming earnings date available')).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Coverage and interpretation limits/));
    expect(screen.getByText('Canadian earnings coverage is unavailable')).toBeInTheDocument();
    expect(screen.queryByText(/Vendor estimate/)).toBeNull();
  });

  it('shows provider failures and retries without fixture fallback', async () => {
    vi.mocked(marketApi.earnings).mockRejectedValueOnce(new Error('Calendar provider unavailable'));
    render(<EarningsPanel symbol="AAPL" />);
    expect(await screen.findByText('Calendar provider unavailable')).toBeInTheDocument();
    expect(screen.queryByText('Dec 5, 2026')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByText('Dec 5, 2026')).toBeInTheDocument();
    expect(marketApi.earnings).toHaveBeenCalledTimes(2);
  });

  it('reloads a keyed component when the ticker changes', async () => {
    const view = render(<EarningsPanel key="AAPL" symbol="AAPL" />);
    await screen.findByText('Dec 5, 2026');
    vi.mocked(marketApi.earnings).mockResolvedValue({
      ...sample,
      symbol: 'NVDA',
      upcoming: null,
      history: [],
    });
    view.rerender(<EarningsPanel key="NVDA" symbol="NVDA" />);
    await screen.findByText('No upcoming earnings date available');
    await waitFor(() => expect(marketApi.earnings).toHaveBeenLastCalledWith('NVDA'));
    expect(screen.queryByText('Dec 5, 2026')).toBeNull();
  });
});
