import { type FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Loading } from '../../../shared/ui/Feedback';
import { PageTitle } from '../../../shared/ui/Presentation';
import { marketApi } from '../../market/api';
import type { SearchResult } from '../../market/types';
import { portfolioApi } from '../../portfolio/api';

export function ResearchLanding() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const watchlist = useResource(portfolioApi.watchlist);
  const navigate = useNavigate();

  const savedSymbols = Array.from(new Set(watchlist.data?.map((item) => item.symbol) ?? []));

  useEffect(() => {
    let active = true;
    const trimmed = query.trim();
    if (!trimmed) {
      setResults([]);
      setError('');
      return;
    }
    const timer = setTimeout(() => {
      setBusy(true);
      marketApi
        .search(trimmed)
        .then((rows) => {
          if (active) {
            setResults(rows);
            setError('');
          }
        })
        .catch((e) => {
          if (active) {
            setResults([]);
            setError(e instanceof Error ? e.message : 'Search unavailable');
          }
        })
        .finally(() => {
          if (active) setBusy(false);
        });
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [query]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;
    const upper = trimmed.toUpperCase();
    const exact = results.find((row) => row.symbol.toUpperCase() === upper);
    if (exact) {
      navigate(`/stocks/${encodeURIComponent(exact.symbol)}`);
      return;
    }
    if (results.length > 0) {
      navigate(`/stocks/${encodeURIComponent(results[0].symbol)}`);
      return;
    }
    setSubmitting(true);
    try {
      const rows = await marketApi.search(trimmed);
      const matched = rows.find((row) => row.symbol.toUpperCase() === upper) ?? rows[0];
      navigate(`/stocks/${encodeURIComponent(matched ? matched.symbol : upper)}`);
    } catch {
      navigate(`/stocks/${encodeURIComponent(upper)}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <>
      <PageTitle title="Stock research" />
      <section className="panel research-search-panel">
        <form className="research-search-form" onSubmit={(event) => void submit(event)} role="search">
          <label className="sr-only" htmlFor="stock-search">
            Search U.S. and Canadian stocks
          </label>
          <input
            id="stock-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            maxLength={64}
            placeholder="Search U.S. ticker or Canadian RY.TO…"
            autoComplete="off"
          />
          <button className="button" type="submit" disabled={!query.trim() || submitting}>
            {submitting ? 'Searching…' : 'Search'}
          </button>
        </form>
        {query.trim() && (
          <div className="research-search-results">
            {busy ? (
              <p className="muted">Searching…</p>
            ) : error ? (
              <p role="alert">{error}</p>
            ) : results.length ? (
              results.map((row) => (
                <Link key={row.symbol} to={`/stocks/${encodeURIComponent(row.symbol)}`}>
                  <strong>{row.symbol}</strong>
                  <span>{row.name}</span>
                  <span>↗</span>
                </Link>
              ))
            ) : (
              <p className="muted">
                No matches yet. Press Search to check source coverage for a U.S. ticker or Canadian .TO / .V
                listing.
              </p>
            )}
          </div>
        )}
      </section>
      <section className="panel research-search-panel" aria-label="My saved stocks">
        <div className="panel-heading">
          <h2>My saved stocks</h2>
          <Link to="/my-stocks">Manage stocks ↗</Link>
        </div>
        {watchlist.loading ? (
          <Loading />
        ) : watchlist.error ? (
          <ErrorBox message={watchlist.error} retry={watchlist.reload} />
        ) : savedSymbols.length ? (
          <div className="ticker-links">
            {savedSymbols.map((symbol) => (
              <Link key={symbol} to={`/stocks/${encodeURIComponent(symbol)}`}>
                {symbol} ↗
              </Link>
            ))}
          </div>
        ) : (
          <Empty>No saved stocks yet. Add stocks to your watchlist to jump straight in.</Empty>
        )}
      </section>
      <div className="notice">
        Missing consensus, provider failures and disputed claims are retained as explicit gaps. Research is
        educational and does not provide investment advice.
      </div>
    </>
  );
}
