import { Link } from 'react-router-dom';
import type { Mode } from '../../../shared/types';
import { ModeBadge } from '../../../shared/ui/Presentation';
import { dateTime, formatNumber, money } from '../../../shared/utils/format';
import type { Review } from '../../intelligence/types';

export function MarketCards({ proxies, mode }: { proxies: Review['proxies']; mode: Mode }) {
  return (
    <div className="market-grid">
      {proxies.map((proxy) => (
        <Link to={`/stocks/${proxy.symbol}`} className="panel market-card" key={proxy.symbol}>
          <div className="row">
            <strong>{proxy.symbol}</strong>
            <span className="muted">ETF proxy</span>
          </div>
          <p>{proxy.name}</p>
          <div className="quote-price">{money(proxy.quote?.price)}</div>
          <p
            className={
              proxy.daily_return_pct === null
                ? 'muted'
                : proxy.daily_return_pct >= 0
                  ? 'positive'
                  : 'negative'
            }
          >
            {proxy.daily_return_pct === null
              ? 'Daily return unavailable'
              : `${proxy.daily_return_pct >= 0 ? '+' : ''}${formatNumber(proxy.daily_return_pct)}% daily return`}
          </p>
          <small>{proxy.quote ? dateTime(proxy.quote.timestamp) : 'Quote unavailable'}</small>
          {proxy.quote && (
            <small>
              {proxy.quote.source_name} · {proxy.quote.stale ? 'stale' : 'provider timestamp'}
              {proxy.quote.delayed ? ' · delayed' : ''}
              {proxy.quote.cached ? ' · cached' : ''}
            </small>
          )}
          <ModeBadge mode={mode} />
        </Link>
      ))}
    </div>
  );
}
