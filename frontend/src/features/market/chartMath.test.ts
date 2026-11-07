import { describe, expect, it } from 'vitest';
import { candleRows, movingAverage, visiblePriceDomain, volumeRows } from './chartMath';
import type { CandleBar } from './types';

const fixture: CandleBar[] = [
  { date: '2026-01-05', open: 100, high: 107, low: 98, close: 105, volume: 1200, adjusted_close: null },
  { date: '2026-01-06', open: 106, high: 108, low: 102, close: 103, volume: null, adjusted_close: 101 },
];

describe('candlestick transformations', () => {
  it('uses documented ECharts OHLC order', () => {
    expect(candleRows(fixture)).toEqual([
      [100, 105, 98, 107],
      [106, 103, 102, 108],
    ]);
  });

  it('preserves missing volume instead of substituting zero', () => {
    expect(volumeRows(fixture).map((row) => row.value)).toEqual([1200, null]);
    expect(volumeRows(fixture)[0].itemStyle.color).not.toBe(volumeRows(fixture)[1].itemStyle.color);
  });

  it('does not invent an MA until enough observations exist', () => {
    expect(movingAverage([10, 20, 30, 40, 50], 3)).toEqual([null, null, 20, 30, 40]);
    expect(movingAverage([10, 20], 5)).toEqual([null, null]);
    expect(movingAverage([5, 5, 5], 1)).toEqual([5, 5, 5]);
  });

  it('rejects invalid periods and non-finite data', () => {
    expect(() => movingAverage([1, 2], 0)).toThrow();
    expect(() => movingAverage([1, 2], 1.5)).toThrow();
    expect(() => movingAverage([1, Number.NaN], 2)).toThrow();
  });
});

describe('zoom-aware price scale', () => {
  it('uses the current visible window rather than forcing an axis from zero', () => {
    const rows: CandleBar[] = [
      { date: '2026-01-02', open: 10, high: 12, low: 9, close: 11, volume: 5, adjusted_close: null },
      { date: '2026-01-05', open: 300, high: 308, low: 297, close: 305, volume: 6, adjusted_close: null },
      { date: '2026-01-06', open: 309, high: 315, low: 305, close: 312, volume: 8, adjusted_close: null },
      { date: '2026-01-07', open: 312, high: 318, low: 307, close: 317, volume: 9, adjusted_close: null },
    ];
    const overall = visiblePriceDomain(rows, [], 0, 100);
    const zoomed = visiblePriceDomain(rows, [], 34, 100);
    expect(overall.min).toBeLessThan(10);
    expect(zoomed.min).toBeGreaterThan(285);
    expect(zoomed.max).toBeLessThan(330);
  });

  it('includes visible moving averages and never invents zero prices', () => {
    const domain = visiblePriceDomain(fixture, [[null, 97]], 0, 100);
    expect(domain.min).toBeLessThan(97);
    expect(domain.min).toBeGreaterThan(0);
    expect(domain.max).toBeGreaterThan(108);
  });

  it('adds headroom when prices are constant and rejects empty inputs', () => {
    const bar: CandleBar = {
      date: '2026-01-05',
      open: 100,
      high: 100,
      low: 100,
      close: 100,
      volume: null,
      adjusted_close: null,
    };
    const domain = visiblePriceDomain([bar], [], 0, 100);
    expect(domain.min).toBeLessThan(100);
    expect(domain.max).toBeGreaterThan(100);
    expect(() => visiblePriceDomain([], [], 0, 100)).toThrow();
  });
});
