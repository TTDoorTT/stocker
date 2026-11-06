import { Link } from 'react-router-dom';
import { ModeBadge } from '../../../shared/ui/Presentation';
import { dateTime, money } from '../../../shared/utils/format';
import type { Stock } from '../types';

export function MarketCards({ stocks }: { stocks: Stock[] }) {
  return (
    <div className="market-grid">
      {stocks.map((stock) => (
        <Link to={`/stocks/${stock.symbol}`} className="panel market-card" key={stock.symbol}>
          <div className="row">
            <strong>{stock.symbol}</strong>
            <span className="muted">ETF proxy</span>
          </div>
          <p>{stock.name}</p>
          <div className="quote-price">{money(stock.quote?.price, stock.currency)}</div>
          <small>{stock.quote ? dateTime(stock.quote.timestamp) : 'Quote unavailable'}</small>
          {stock.quote && (
            <small>
              {stock.quote.source_name} · {stock.quote.stale ? 'stale' : 'provider timestamp'}
              {stock.quote.delayed ? ' · delayed' : ''}
              {stock.quote.cached ? ' · cached' : ''}
            </small>
          )}
          <ModeBadge mode={stock.mode} />
        </Link>
      ))}
    </div>
  );
}
