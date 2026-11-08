import { describe, expect, it } from 'vitest';
import { driftBounds, eventPath, formatDrift, formatPositiveShare, meanPath } from './eventStudyMath';
import type { EventStudyResponse, EventWindow } from './types';

const eventId = (n: number) => `US:AAPL:earnings_release:FY${2020 + Math.floor(n / 4)}Q${(n % 4) + 1}`;
const event = (n: number, eligible = true): EventWindow => ({
  event_id: eventId(n),
  eligible,
  day_zero: eligible ? '2026-04-10' : null,
  exclusion_reason: eligible ? null : 'Incomplete window',
  excess_returns: eligible
    ? Object.fromEntries(Array.from({ length: 26 }, (_, index) => [String(index - 5), index - 5 + n]))
    : {},
});
const study = (rows: EventWindow[], hasSummary: boolean): EventStudyResponse => ({
  symbol: 'AAPL',
  market: 'US',
  currency: 'USD',
  mode: 'fixtures',
  benchmark_symbol: 'SPY',
  pre_trading_days: 5,
  post_trading_days: 20,
  return_method: 'compounded_close_to_close_excess',
  minimum_sample: 8,
  eligible_event_count: rows.filter((row) => row.eligible).length,
  events: rows,
  summary: hasSummary
    ? [
        {
          horizon: '+5',
          eligible_n: rows.length,
          mean_excess_return: 4,
          median_excess_return: 4,
          positive_share: 0.5,
        },
      ]
    : null,
  sources: [],
  gaps: [],
});

describe('event study display-only calculations', () => {
  it('maps an entire -5 to +20-day path without filling holes', () => {
    const path = eventPath(event(0));
    expect(path).toHaveLength(26);
    expect(path[0]).toEqual({ day: -5, value: -5 });
    expect(path.at(-1)).toEqual({ day: 20, value: 20 });
    const broken = event(0);
    broken.excess_returns['7'] = null;
    expect(eventPath(broken)).toEqual([]);
    expect(eventPath(event(0, false))).toEqual([]);
  });

  it('requires at least eight completed paths and backend summary before an aggregate', () => {
    const rows = Array.from({ length: 8 }, (_, index) => event(index));
    expect(meanPath(study(rows.slice(0, 7), false))).toEqual([]);
    expect(meanPath(study(rows, false))).toEqual([]);
    const avg = meanPath(study(rows, true));
    expect(avg).toHaveLength(26);
    expect(avg.find((point) => point.day === 0)?.value).toBe(3.5);
    rows[1].excess_returns['8'] = null;
    expect(meanPath(study(rows, true))).toEqual([]);
  });

  it('scales around zero and distinguishes percentage points from percent shares', () => {
    const bounds = driftBounds([
      { day: 0, value: 8 },
      { day: 1, value: 11 },
    ]);
    expect(bounds?.minimum).toBeLessThan(0);
    expect(bounds?.maximum).toBeGreaterThan(11);
    expect(driftBounds([])).toBeNull();
    expect(formatDrift(-2.123)).toBe('-2.12 pp');
    expect(formatDrift(1.25)).toBe('+1.25 pp');
    expect(formatDrift(null)).toBe('—');
    expect(formatPositiveShare(0.625)).toBe('62.5%');
  });
});
