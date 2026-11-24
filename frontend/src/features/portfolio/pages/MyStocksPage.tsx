import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Loading } from '../../../shared/ui/Feedback';
import { PageTitle } from '../../../shared/ui/Presentation';
import { portfolioApi } from '../api';

export function MyStocks() {
  const watchlist = useResource(portfolioApi.watchlist);
  const [error, setError] = useState('');

  async function removeWatch(value: string) {
    setError('');
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
        {error && <ErrorBox message={error} />}
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
                  type="button"
                  className="link-button"
                  aria-label={`Remove ${item.symbol} from watchlist`}
                  onClick={() => void removeWatch(item.symbol)}
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
    </>
  );
}
