import { type FormEvent, useState } from 'react';
import { Link } from 'react-router-dom';
import { portfolioApi } from '../features/portfolio/api';
import { useResource } from '../shared/hooks/useResource';
import { Empty, ErrorBox, Loading } from '../shared/ui/Feedback';
import { ModeBadge, PageTitle, SourceLink } from '../shared/ui/Presentation';
import { dateTime, formatNumber, money } from '../shared/utils/format';
export function MyStocks() {
  const watchlist = useResource(portfolioApi.watchlist);
  const positions = useResource(portfolioApi.positions);
  const [symbol, setSymbol] = useState('');
  const [shares, setShares] = useState('');
  const [cost, setCost] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  async function add(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await portfolioApi.position({
        symbol: symbol.toUpperCase(),
        shares: Number(shares),
        average_cost: Number(cost),
        currency: /\.(TO|V)$/i.test(symbol.trim()) ? 'CAD' : 'USD',
      });
      positions.reload();
      setSymbol('');
      setShares('');
      setCost('');
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Position could not be saved');
    } finally {
      setBusy(false);
    }
  }
  async function removePosition(id: number) {
    try {
      await portfolioApi.removePosition(id);
      positions.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Position could not be removed');
    }
  }
  async function removeWatch(value: string) {
    try {
      await portfolioApi.unwatch(value);
      watchlist.reload();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Stock could not be removed');
    }
  }
  return (
    <>
      <PageTitle title="My stocks" />
      <section className="panel">
        <div className="panel-heading">
          <h2>Watchlist</h2>
          <Link to="/research">Find a company ↗</Link>
        </div>
        {watchlist.loading ? (
          <Loading />
        ) : watchlist.error ? (
          <ErrorBox message={watchlist.error} retry={watchlist.reload} />
        ) : watchlist.data?.length ? (
          <div className="watch-grid">
            {watchlist.data.map((item) => (
              <div key={item.symbol}>
                <Link to={`/stocks/${item.symbol}`}>
                  <strong>{item.symbol}</strong> ↗
                </Link>
                <button
                  className="link-button"
                  aria-label={`Remove ${item.symbol} from watchlist`}
                  onClick={() => removeWatch(item.symbol)}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        ) : (
          <Empty>Your watchlist is empty. Add a company from its stock overview.</Empty>
        )}
      </section>
      <section className="panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">MANUAL HOLDINGS SNAPSHOT</p>
            <h2>Simple positions</h2>
          </div>
          <span className="badge">USD / CAD</span>
        </div>
        <p className="muted">
          Unrealized P&amp;L uses sourced quotes in the listing currency (no automatic FX conversion).
          Canadian quotes may be unavailable. It uses and entered average cost. This snapshot does not track
          transactions or realized returns.
        </p>
        <form className="position-form" onSubmit={add}>
          <label>
            Ticker
            <input
              required
              maxLength={10}
              value={symbol}
              placeholder="AAPL or RY.TO"
              onChange={(e) => setSymbol(e.target.value)}
            />
          </label>
          <label>
            Shares
            <input
              required
              type="number"
              min="0.000001"
              step="any"
              value={shares}
              placeholder="10"
              onChange={(e) => setShares(e.target.value)}
            />
          </label>
          <label>
            Average cost ({/\.(TO|V)$/i.test(symbol.trim()) ? 'CAD' : 'USD'})
            <input
              required
              type="number"
              min="0"
              step="any"
              value={cost}
              placeholder="0.00"
              onChange={(e) => setCost(e.target.value)}
            />
          </label>
          <button className="button" disabled={busy}>
            {busy ? 'Saving…' : 'Add position'}
          </button>
        </form>
        {error && <ErrorBox message={error} />}{' '}
        {positions.loading ? (
          <Loading />
        ) : positions.error ? (
          <ErrorBox message={positions.error} retry={positions.reload} />
        ) : positions.data?.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Symbol</th>
                  <th>Shares</th>
                  <th>Average cost</th>
                  <th>Sourced price</th>
                  <th>Unrealized P&amp;L</th>
                  <th>Action</th>
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
                            {position.quote.cached ? ' · cached' : ''}
                          </small>
                        </>
                      )}
                    </td>
                    <td
                      className={
                        position.unrealized_pnl === null
                          ? ''
                          : position.unrealized_pnl >= 0
                            ? 'positive'
                            : 'negative'
                      }
                    >
                      {money(position.unrealized_pnl, position.currency)}
                    </td>
                    <td>
                      <button
                        className="link-button"
                        onClick={() => removePosition(position.id)}
                        aria-label={`Delete ${position.symbol} position`}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty>No positions saved yet.</Empty>
        )}
      </section>
    </>
  );
}
