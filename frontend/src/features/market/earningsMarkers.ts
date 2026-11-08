import type { CandleBar, CandleInterval, EarningsEvent } from './types';

/** An earnings date maps to a trading bar or to a clearly labeled week/month bucket.
 * Never move a date-only event to the next trading session and imply release timing.
 */
export interface EarningsMarker {
  candleDate: string;
  candleIndex: number;
  anchorPrice: number;
  events: EarningsEvent[];
}

export interface MarkerAlignment {
  markers: EarningsMarker[];
  outsideRange: number;
  unaligned: number;
}

function dateKey(value: string, interval: CandleInterval): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.valueOf()) || date.toISOString().slice(0, 10) !== value) return null;
  if (interval === '1d') return value;
  if (interval === '1mo') return value.slice(0, 7);
  // ISO week, always in UTC; ISO week-year can differ from calendar year.
  const day = date.getUTCDay() || 7;
  date.setUTCDate(date.getUTCDate() + 4 - day);
  const weekYear = date.getUTCFullYear();
  const january4 = new Date(Date.UTC(weekYear, 0, 4));
  const janDay = january4.getUTCDay() || 7;
  january4.setUTCDate(january4.getUTCDate() + 4 - janDay);
  const week = 1 + Math.round((date.getTime() - january4.getTime()) / (7 * 86400000));
  return `${weekYear}-W${String(week).padStart(2, '0')}`;
}

/** Group events on candle dates. Daily mapping requires an *exact* trading-date match. */
export function alignEarningsMarkers(
  bars: readonly CandleBar[],
  interval: CandleInterval,
  events: readonly EarningsEvent[],
): MarkerAlignment {
  if (bars.length === 0) return { markers: [], outsideRange: events.length, unaligned: 0 };
  const barLookup = new Map<string, number>();
  bars.forEach((bar, index) => {
    const key = dateKey(bar.date, interval);
    if (key) barLookup.set(key, index);
  });
  const selected = new Map<number, EarningsEvent[]>();
  let outsideRange = 0;
  let unaligned = 0;
  const earliest = bars[0].date;
  const latest = bars[bars.length - 1].date;
  const beginKey = dateKey(earliest, interval);
  const endKey = dateKey(latest, interval);

  for (const event of events) {
    const key = dateKey(event.event_date, interval);
    if (key === null) {
      unaligned += 1;
      continue;
    }
    if (event.event_date > latest) {
      outsideRange += 1;
      continue;
    }
    const index = barLookup.get(key);
    if (index === undefined) {
      if (beginKey && endKey && (key < beginKey || key > endKey)) outsideRange += 1;
      else unaligned += 1;
      continue;
    }
    selected.set(index, [...(selected.get(index) ?? []), event]);
  }
  const markers = [...selected.entries()]
    .sort(([a], [b]) => a - b)
    .map(([index, rows]) => ({
      candleDate: bars[index].date,
      candleIndex: index,
      anchorPrice: bars[index].high,
      events: rows.sort((a, b) => a.event_date.localeCompare(b.event_date)),
    }));
  return { markers, outsideRange, unaligned };
}
