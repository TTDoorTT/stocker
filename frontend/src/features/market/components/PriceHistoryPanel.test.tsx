import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { marketApi } from '../api';
import type { CandleSeries } from '../types';
import { PriceHistoryPanel } from './PriceHistoryPanel';

vi.mock('../api', () => ({ marketApi: { candles: vi.fn() } }));
vi.mock('./CandleChart', () => ({
  CandleChart: ({ series }: { series: CandleSeries }) => (
    <div data-testid="candles">
      {series.symbol} · {series.bars.length} observations
    </div>
  ),
}));

const sample: CandleSeries = {
  symbol: 'AAPL',
  market: 'US',
  currency: 'USD',
  mode: 'fixtures',
  range: '6m',
  interval: '1d',
  price_basis: 'provider_ohlc',
  adjustment_note: 'Synthetic OHLC only',
  source: {
    name: 'Synthetic fixture',
    url: 'https://example.invalid/synthetic',
    fetched_at: '2026-01-01T00:00:00Z',
    published_at: null,
    cached: false,
    fixture: true,
  },
  bars: [
    { date: '2025-12-30', open: 10, high: 12, low: 9, close: 11, volume: 500, adjusted_close: null },
    { date: '2025-12-31', open: 11, high: 13, low: 10, close: 12, volume: 600, adjusted_close: null },
  ],
  gaps: [],
};

beforeEach(() => {
  vi.mocked(marketApi.candles).mockReset();
  vi.mocked(marketApi.candles).mockResolvedValue(sample);
});

describe('price history panel', () => {
  it('loads candles and sends the selected range and interval to the API', async () => {
    render(<PriceHistoryPanel symbol="AAPL" mode="fixtures" />);
    expect(await screen.findByTestId('candles')).toHaveTextContent('AAPL');
    expect(marketApi.candles).toHaveBeenCalledWith('AAPL', '6m', '1d');

    fireEvent.click(screen.getByRole('button', { name: '3m' }));
    await waitFor(() => expect(marketApi.candles).toHaveBeenLastCalledWith('AAPL', '3m', '1d'));
    expect(screen.getByRole('button', { name: '3m' })).toHaveAttribute('aria-pressed', 'true');

    fireEvent.change(screen.getByLabelText('Interval'), { target: { value: '1wk' } });
    await waitFor(() => expect(marketApi.candles).toHaveBeenLastCalledWith('AAPL', '3m', '1wk'));
  });

  it('displays failures and can retry without fabricating history', async () => {
    vi.mocked(marketApi.candles).mockRejectedValueOnce(new Error('Provider unavailable'));
    render(<PriceHistoryPanel symbol="AAPL" mode="live" />);
    expect(await screen.findByText('Provider unavailable')).toBeInTheDocument();
    expect(screen.queryByTestId('candles')).toBeNull();
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }));
    expect(await screen.findByTestId('candles')).toBeInTheDocument();
    expect(marketApi.candles).toHaveBeenCalledTimes(2);
  });

  it('resets state and reloads for a newly keyed ticker', async () => {
    const view = render(<PriceHistoryPanel key="AAPL" symbol="AAPL" mode="fixtures" />);
    await screen.findByTestId('candles');
    fireEvent.click(screen.getByRole('button', { name: '3m' }));
    await waitFor(() => expect(marketApi.candles).toHaveBeenLastCalledWith('AAPL', '3m', '1d'));
    vi.mocked(marketApi.candles).mockResolvedValue({ ...sample, symbol: 'NVDA' });
    view.rerender(<PriceHistoryPanel key="NVDA" symbol="NVDA" mode="fixtures" />);
    expect(await screen.findByTestId('candles')).toHaveTextContent('NVDA');
    expect(marketApi.candles).toHaveBeenLastCalledWith('NVDA', '6m', '1d');
  });
});
