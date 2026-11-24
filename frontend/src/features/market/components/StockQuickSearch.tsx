import { type FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { marketApi } from '../api';
import type { SearchResult } from '../types';

export function StockQuickSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const navigate = useNavigate();

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
      setQuery('');
      navigate(`/stocks/${encodeURIComponent(exact.symbol)}`);
      return;
    }
    if (results.length > 0) {
      setQuery('');
      navigate(`/stocks/${encodeURIComponent(results[0].symbol)}`);
      return;
    }
    setSubmitting(true);
    try {
      const rows = await marketApi.search(trimmed);
      const matched = rows.find((row) => row.symbol.toUpperCase() === upper) ?? rows[0];
      setQuery('');
      navigate(`/stocks/${encodeURIComponent(matched ? matched.symbol : upper)}`);
    } catch {
      setQuery('');
      navigate(`/stocks/${encodeURIComponent(upper)}`);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="panel stock-quick-search" aria-label="Jump to another stock">
      <form className="research-search-form" onSubmit={(event) => void submit(event)} role="search">
        <label className="sr-only" htmlFor="stock-quick-search">
          Jump to another stock
        </label>
        <input
          id="stock-quick-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={64}
          placeholder="Switch stock by ticker or name (e.g., MSFT, NVDA, RY.TO)…"
          autoComplete="off"
        />
        <button className="button secondary" type="submit" disabled={!query.trim() || submitting}>
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
              <Link
                key={row.symbol}
                to={`/stocks/${encodeURIComponent(row.symbol)}`}
                onClick={() => setQuery('')}
              >
                <strong>{row.symbol}</strong>
                <span>{row.name}</span>
                <span>↗</span>
              </Link>
            ))
          ) : (
            <p className="muted">No matches yet. Press Search to open the entered ticker directly.</p>
          )}
        </div>
      )}
    </section>
  );
}
