import type { CandleBar } from './types';

/** Simple moving average over consecutive sourced bars; no invented earlier values. */
export function movingAverage(values: number[], period: number): (number | null)[] {
  if (!Number.isInteger(period) || period < 1) throw new Error('Invalid moving-average period');
  if (values.some((value) => !Number.isFinite(value))) throw new Error('Invalid price value');
  let sum = 0;
  return values.map((value, index) => {
    sum += value;
    if (index >= period) sum -= values[index - period];
    return index >= period - 1 ? sum / period : null;
  });
}

/** ECharts candlestick order is [open, close, low, high]. */
export function candleRows(bars: CandleBar[]): number[][] {
  return bars.map(({ open, close, low, high }) => [open, close, low, high]);
}

/** No trading volume is represented as null, never a fabricated zero. */
export function volumeRows(bars: CandleBar[]) {
  return bars.map(({ open, close, volume }) => ({
    value: volume,
    itemStyle: { color: close >= open ? '#299c7c' : '#d76877' },
  }));
}

/** Calculate a tight, positive price domain from candles and averages visible after zoom. */
export function visiblePriceDomain(
  bars: CandleBar[],
  averages: ReadonlyArray<ReadonlyArray<number | null>>,
  startPercent: number,
  endPercent: number,
): { min: number; max: number } {
  if (bars.length === 0) throw new Error('Cannot scale an empty price chart');
  const limit = (value: number) => Math.max(0, Math.min(100, Number.isFinite(value) ? value : 0));
  const start = Math.floor(((bars.length - 1) * Math.min(limit(startPercent), limit(endPercent))) / 100);
  const end = Math.ceil(((bars.length - 1) * Math.max(limit(startPercent), limit(endPercent))) / 100);
  let low = Infinity;
  let high = -Infinity;
  for (let i = start; i <= end; i++) {
    low = Math.min(low, bars[i].low);
    high = Math.max(high, bars[i].high);
    for (const average of averages) {
      const value = average[i];
      if (value !== null && value !== undefined && Number.isFinite(value)) {
        low = Math.min(low, value);
        high = Math.max(high, value);
      }
    }
  }
  const pad = Math.max((high - low) * 0.075, high * 0.006, 0.01);
  return { min: Math.max(0.01, low - pad), max: high + pad };
}
