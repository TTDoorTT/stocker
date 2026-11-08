import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { marketApi } from '../api';
import type { EventStudyResponse, EventsResponse } from '../types';
import { EventStudyPanel } from './EventStudyPanel';

vi.mock('../api', () => ({ marketApi: { events: vi.fn(), eventStudy: vi.fn() } }));

const source = {
  name: 'SYNTHETIC historical events',
  url: 'https://example.org/fixture',
  fetched_at: '2026-11-07T19:00:00Z',
  published_at: null,
  cached: false,
  fixture: true,
};
const id = 'US:AAPL:earnings_release:FY2026Q3';
const dated: EventsResponse = {
  symbol: 'AAPL',
  market: 'US',
  currency: 'USD',
  mode: 'fixtures',
  events: [
    {
      event_id: id,
      fiscal_year: 2026,
      fiscal_quarter: 'Q3',
      event_date: '2026-07-30',
      published_at: null,
      date_precision: 'date_only',
      timing_basis: 'vendor_report',
      source,
    },
  ],
  sources: [source],
  gaps: ['Invented dates'],
};
const study: EventStudyResponse = {
  symbol: 'AAPL',
  market: 'US',
  currency: 'USD',
  mode: 'fixtures',
  benchmark_symbol: 'SPY',
  pre_trading_days: 5,
  post_trading_days: 20,
  return_method: 'compounded_close_to_close_excess',
  minimum_sample: 8,
  eligible_event_count: 1,
  summary: null,
  events: [
    {
      event_id: id,
      eligible: true,
      day_zero: '2026-07-31',
      exclusion_reason: null,
      excess_returns: Object.fromEntries(
        Array.from({ length: 26 }, (_, index) => [String(index - 5), (index - 5) / 2]),
      ),
    },
  ],
  sources: [source],
  gaps: ['Initial price jump excluded'],
};

beforeEach(() => {
  vi.mocked(marketApi.events).mockReset().mockResolvedValue(dated);
  vi.mocked(marketApi.eventStudy).mockReset().mockResolvedValue(study);
});

describe('historical event study panel', () => {
  it('loads dates on mount but runs price study only on explicit click', async () => {
    render(<EventStudyPanel symbol="AAPL" />);
    expect(await screen.findByText('1 dated historical event(s) available')).toBeInTheDocument();
    expect(marketApi.events).toHaveBeenCalledWith('AAPL');
    expect(marketApi.eventStudy).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole('button', { name: 'Run event study' }));
    await waitFor(() => expect(marketApi.eventStudy).toHaveBeenCalledWith('AAPL'));
    expect(
      await screen.findByRole('img', { name: 'SPY-relative post-date drift chart' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Aggregate statistics withheld/)).toBeInTheDocument();
    expect(screen.getByText('2026-07-30')).toBeInTheDocument();
  });

  it('keeps unavailable data absent and never calls price endpoint without events', async () => {
    vi.mocked(marketApi.events).mockResolvedValue({
      ...dated,
      market: 'CA',
      symbol: 'RY.TO',
      currency: 'CAD',
      mode: 'live',
      events: [],
      sources: [],
      gaps: ['No Canadian coverage'],
    });
    render(<EventStudyPanel symbol="RY.TO" />);
    expect(await screen.findByText('0 dated historical event(s) available')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Run event study' })).toBeDisabled();
    expect(marketApi.eventStudy).not.toHaveBeenCalled();
    expect(
      screen.getByText('No usable earnings dates are available for an event study.'),
    ).toBeInTheDocument();
  });

  it('displays an API failure and retries only when requested', async () => {
    vi.mocked(marketApi.eventStudy).mockRejectedValueOnce(new Error('Price history unavailable'));
    render(<EventStudyPanel symbol="AAPL" />);
    await screen.findByText('1 dated historical event(s) available');
    fireEvent.click(screen.getByRole('button', { name: 'Run event study' }));
    expect(await screen.findByText('Price history unavailable')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(
      await screen.findByRole('img', { name: 'SPY-relative post-date drift chart' }),
    ).toBeInTheDocument();
    expect(marketApi.eventStudy).toHaveBeenCalledTimes(2);
  });

  it('resets data and request state when ticker key changes', async () => {
    const view = render(<EventStudyPanel key="AAPL" symbol="AAPL" />);
    await screen.findByText('1 dated historical event(s) available');
    fireEvent.click(screen.getByRole('button', { name: 'Run event study' }));
    await screen.findByRole('img', { name: 'SPY-relative post-date drift chart' });
    vi.mocked(marketApi.events).mockResolvedValue({ ...dated, symbol: 'NVDA', events: [] });
    view.rerender(<EventStudyPanel key="NVDA" symbol="NVDA" />);
    expect(await screen.findByText('0 dated historical event(s) available')).toBeInTheDocument();
    expect(screen.queryByRole('img', { name: 'SPY-relative post-date drift chart' })).not.toBeInTheDocument();
    expect(marketApi.events).toHaveBeenLastCalledWith('NVDA');
  });
});
