import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { Heatmap } from '../components/Heatmap';
import {
  Empty,
  ErrorBox,
  Loading,
  ModeBadge,
  PageTitle,
  SourceLink,
  dateTime,
  formatNumber,
  money,
  useResource,
} from '../components/shared';
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
export function Home() {
  const overview = useResource(api.overview);
  const watchlist = useResource(api.watchlist);
  return (
    <>
      <PageTitle title="Market workspace">
        <span className="badge">United States</span>
      </PageTitle>
      <section className="hero">
        <div>
          <p className="eyebrow">RESEARCH WITH A RECORD</p>
          <h2>
            A clearer view.
            <br />
            An evidence trail.
          </h2>
          <p>
            Follow six specialist agents from company identity to a cited report. Review every source,
            calculation and validation decision.
          </p>
          <Link className="button" to="/research">
            Explore stock research <span>↗</span>
          </Link>
        </div>
        <div className="pipeline-mini" aria-label="Research stages">
          {['Profile', 'Financials', 'Expectations', 'Valuation', 'Risk', 'Report'].map((stage, i) => (
            <div key={stage}>
              <span>0{i + 1}</span>
              {stage}
              <b>{i === 5 ? '✓' : '→'}</b>
            </div>
          ))}
        </div>
      </section>
      <div className="section-title">
        <h2>Market overview</h2>
        <p className="muted">Liquid ETF prices as market proxies; these are not index levels.</p>
      </div>
      {overview.loading ? (
        <Loading />
      ) : overview.error ? (
        <ErrorBox message={overview.error} retry={overview.reload} />
      ) : overview.data?.length ? (
        <MarketCards stocks={overview.data} />
      ) : (
        <Empty>Market quotes unavailable.</Empty>
      )}
      <Heatmap />
      <PositionsPreview />
      <section className="panel">
        <div className="panel-heading">
          <h2>Your watchlist</h2>
          <Link to="/my-stocks">Manage stocks ↗</Link>
        </div>
        {watchlist.loading ? (
          <Loading />
        ) : watchlist.error ? (
          <ErrorBox message={watchlist.error} />
        ) : watchlist.data?.length ? (
          <div className="ticker-links">
            {watchlist.data.map(({ symbol }) => (
              <Link key={symbol} to={`/stocks/${symbol}`}>
                {symbol} ↗
              </Link>
            ))}
          </div>
        ) : (
          <Empty>Add a stock from its overview page to keep it close.</Empty>
        )}
      </section>
    </>
  );
}

function PositionsPreview() {
  const positions = useResource(api.positions);
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Simple positions</h2>
        <Link to="/my-stocks">Manage positions ↗</Link>
      </div>
      <p className="muted">
        Manual holdings snapshot. Unrealized P&amp;L uses sourced quotes and entered average cost.
      </p>
      {positions.loading ? (
        <Loading />
      ) : positions.error ? (
        <ErrorBox message={positions.error} retry={positions.reload} />
      ) : positions.data?.length ? (
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                <th>Company</th>
                <th>Shares</th>
                <th>Average cost</th>
                <th>Quote / source</th>
                <th>Unrealized P&amp;L</th>
              </tr>
            </thead>
            <tbody>
              {positions.data.map((position) => (
                <tr key={position.id}>
                  <td>
                    <Link to={`/stocks/${position.symbol}`}>{position.symbol}</Link>
                    <br />
                    <ModeBadge mode={position.mode} />
                  </td>
                  <td>{formatNumber(position.shares, 6)}</td>
                  <td>{money(position.average_cost, position.currency)}</td>
                  <td>
                    {money(position.quote_price, position.currency)}
                    {position.quote && (
                      <>
                        <small>
                          <SourceLink url={position.quote.source_url} name={position.quote.source_name} />
                        </small>
                        <small>
                          {dateTime(position.quote.timestamp)} ·{' '}
                          {position.quote.stale ? 'stale' : 'provider timestamp'}
                          {position.quote.delayed ? ' · delayed' : ''}
                          {position.quote.cached ? ' · cached' : ''}
                        </small>
                      </>
                    )}
                  </td>
                  <td>{money(position.unrealized_pnl, position.currency)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <Empty>No positions saved. Add a simple position in My Stocks.</Empty>
      )}
    </section>
  );
}
