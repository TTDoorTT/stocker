import { useState } from 'react';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge } from '../../../shared/ui/Presentation';
import { marketApi } from '../api';
import type { CandleInterval, CandleRange, Stock } from '../types';
import { CandleChart } from './CandleChart';

const ranges: CandleRange[] = ['1m', '3m', '6m', '1y', '2y', '5y'];

/** Key by symbol from the parent page to reset controls on listing changes. */
export function PriceHistoryPanel({ symbol, mode }: { symbol: string; mode: Stock['mode'] }) {
  const [range, setRange] = useState<CandleRange>('6m');
  const [interval, setInterval] = useState<CandleInterval>('1d');
  const candles = useResource(() => marketApi.candles(symbol, range, interval), [symbol, range, interval]);

  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Price history · OHLCV</h2>
        <ModeBadge mode={mode} />
      </div>
      <div className="candle-controls" aria-label="Price chart controls">
        <div className="candle-ranges" role="group" aria-label="Historical range">
          {ranges.map((value) => (
            <button type="button" key={value} aria-pressed={range === value} onClick={() => setRange(value)}>
              {value}
            </button>
          ))}
        </div>
        <label htmlFor="stock-candle-interval">
          Interval
          <select
            id="stock-candle-interval"
            value={interval}
            onChange={(event) => setInterval(event.target.value as CandleInterval)}
          >
            <option value="1d">Daily</option>
            <option value="1wk">Weekly</option>
            <option value="1mo">Monthly</option>
          </select>
        </label>
        <button type="button" onClick={candles.reload}>
          Refresh
        </button>
      </div>
      {candles.loading ? (
        <Loading />
      ) : candles.error ? (
        <ErrorBox message={candles.error} retry={candles.reload} />
      ) : candles.data ? (
        <CandleChart series={candles.data} />
      ) : (
        <Empty>No sourced candlestick observations are available.</Empty>
      )}
    </section>
  );
}
