import { Link } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, SourceLink } from '../../../shared/ui/Presentation';
import { dateTime, formatNumber, money } from '../../../shared/utils/format';
import { portfolioApi } from '../api';

export function PositionsPreview() {
  const positions = useResource(portfolioApi.positions);
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
