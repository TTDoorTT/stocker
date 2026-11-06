import { type FormEvent, useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import type { SearchResult } from '../types';

export function StockSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  useEffect(() => {
    let active = true;
    if (query.trim().length < 1) {
      setResults([]);
      return;
    }
    const timer = setTimeout(() => {
      setBusy(true);
      api
        .search(query.trim())
        .then((rows) => {
          if (active) {
            setResults(rows);
            setError('');
          }
        })
        .catch((e) => {
          if (active) {
            setResults([]);
            setError(e.message);
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
  function submit(event: FormEvent) {
    event.preventDefault();
    const symbol = results[0]?.symbol || query.trim().toUpperCase();
    if (symbol) {
      setQuery('');
      navigate(`/stocks/${encodeURIComponent(symbol)}`);
    }
  }
  return (
    <div className="search">
      <form onSubmit={submit} role="search">
        <label className="sr-only" htmlFor="stock-search">
          Search U.S. and Canadian stocks
        </label>
        <span aria-hidden="true">⌕</span>
        <input
          id="stock-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          maxLength={64}
          placeholder="Search U.S. ticker or Canadian RY.TO…"
          autoComplete="off"
        />
        <button className="button secondary" type="submit" disabled={!query.trim()}>
          Analyze
        </button>
      </form>
      {query && (
        <div className="search-results">
          {busy ? (
            <p>Searching…</p>
          ) : error ? (
            <p role="alert">{error}</p>
          ) : results.length ? (
            results.map((row) => (
              <Link onClick={() => setQuery('')} key={row.symbol} to={`/stocks/${row.symbol}`}>
                <strong>{row.symbol}</strong>
                <span>{row.name}</span>
                <span>↗</span>
              </Link>
            ))
          ) : (
            <p>No matches. Enter a U.S. ticker or a Canadian .TO / .V listing to check source coverage.</p>
          )}
        </div>
      )}
    </div>
  );
}
