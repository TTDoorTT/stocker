import { describe, expect, it } from 'vitest';
import { alignEarningsMarkers } from './earningsMarkers';
import type { CandleBar, EarningsEvent } from './types';

const source = {
  name: 'Synthetic calendar',
  url: 'https://example.org/fixture',
  fetched_at: '2026-11-07T00:00:00Z',
  published_at: null,
  cached: false,
  fixture: true,
};
const event = (date: string, quarter: EarningsEvent['fiscal_quarter'] = 'Q1'): EarningsEvent => ({
  event_id: `US:AAPL:earnings_release:FY2026${quarter}`,
  fiscal_year: 2026,
  fiscal_quarter: quarter,
  event_date: date,
  published_at: null,
  date_precision: 'date_only',
  timing_basis: 'vendor_report',
  source,
});
const bar = (date: string): CandleBar => ({
  date,
  open: 100,
  high: 110,
  low: 90,
  close: 104,
  volume: 1000,
  adjusted_close: null,
});

describe('date-only earnings markers', () => {
  it('maps only exact daily trading dates, never shifts weekend events to Monday', () => {
    const result = alignEarningsMarkers([bar('2026-07-30'), bar('2026-07-31'), bar('2026-08-03')], '1d', [
      event('2026-07-31'),
      event('2026-08-01', 'Q2'),
    ]);
    expect(result.markers).toHaveLength(1);
    expect(result.markers[0].candleDate).toBe('2026-07-31');
    expect(result.markers[0].events[0].fiscal_quarter).toBe('Q1');
    expect(result.unaligned).toBe(1);
  });

  it('places dates into clearly labeled weekly buckets across ISO year boundaries', () => {
    const result = alignEarningsMarkers([bar('2025-12-31'), bar('2026-01-09')], '1wk', [
      event('2026-01-01'),
      event('2026-01-08', 'Q2'),
    ]);
    expect(result.markers.map((marker) => marker.candleDate)).toEqual(['2025-12-31', '2026-01-09']);
  });

  it('maps monthly events without fabricating an exact trading session', () => {
    const result = alignEarningsMarkers([bar('2026-06-30'), bar('2026-07-31')], '1mo', [
      event('2026-07-04'),
      event('2026-07-18', 'Q2'),
    ]);
    expect(result.markers).toHaveLength(1);
    expect(result.markers[0].events).toHaveLength(2);
    expect(result.markers[0].candleDate).toBe('2026-07-31');
  });

  it('reports out-of-range and invalid dates instead of moving markers', () => {
    const result = alignEarningsMarkers([bar('2026-07-30'), bar('2026-07-31')], '1d', [
      event('2026-05-06'),
      event('2026-08-05', 'Q2'),
      event('2026-02-30', 'Q3'),
    ]);
    expect(result.markers).toHaveLength(0);
    expect(result.outsideRange).toBe(2);
    expect(result.unaligned).toBe(1);
  });

  it('empty series cannot invent any marker price', () => {
    expect(alignEarningsMarkers([], '1d', [event('2026-07-31')])).toEqual({
      markers: [],
      outsideRange: 1,
      unaligned: 0,
    });
  });
});
