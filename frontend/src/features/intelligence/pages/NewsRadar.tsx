import { useCallback, useEffect, useRef, useState } from 'react';

import { Empty, ErrorBox, Loading } from '../../../shared/ui/Feedback';
import { PageTitle } from '../../../shared/ui/Presentation';
import { dateTime } from '../../../shared/utils/format';
import { intelligenceApi } from '../api';
import { RSSHighlights } from '../components/RSSHighlights';
import type { RSSNewsResponse } from '../types';

export function NewsRadar() {
  const [category, setCategory] = useState('ai');
  const activeCategory = useRef('ai');

  const [data, setData] = useState<RSSNewsResponse>();
  const [error, setError] = useState('');
  const [refreshError, setRefreshError] = useState('');
  const [refreshingRequest, setRefreshingRequest] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await intelligenceApi.rss(category);
      if (activeCategory.current !== category) return;
      setData(response);
      setError('');
    } catch (err) {
      if (activeCategory.current === category) {
        setError(err instanceof Error ? err.message : 'News unavailable');
      }
    }
  }, [category]);

  useEffect(() => {
    void load();
  }, [load]);

  // Poll while the background RSS collector is working.
  useEffect(() => {
    if (!data?.refreshing) return;
    const handle = window.setInterval(() => {
      void load();
    }, 3000);
    return () => window.clearInterval(handle);
  }, [data?.refreshing, load]);

  async function refresh() {
    setRefreshingRequest(true);
    setRefreshError('');
    try {
      await intelligenceApi.refreshRSS();
      await load();
    } catch (err) {
      setRefreshError(err instanceof Error ? err.message : 'Unable to refresh');
    } finally {
      setRefreshingRequest(false);
    }
  }

  function chooseCategory(next: string) {
    if (next === category) return;
    activeCategory.current = next;
    setCategory(next);
    setData(undefined);
    setError('');
  }

  return (
    <>
      <PageTitle title="Industry intelligence" />
      <section className="panel">
        <div className="rss-toolbar">
          <div>
            <h2>Investment News</h2>
            <p className="muted">English-language investment and industry news from curated RSS sources.</p>
            {data && (
              <small>
                {data.sources_ok}/{data.sources_total} sources responded · Last successful refresh:{' '}
                {data.last_refreshed ? dateTime(data.last_refreshed) : 'Not yet'}
                {data.refreshing ? ' · Refreshing in background…' : ''}
              </small>
            )}
          </div>
          <button
            type="button"
            className="button secondary"
            onClick={() => void refresh()}
            disabled={refreshingRequest || data?.refreshing}
          >
            {refreshingRequest || data?.refreshing ? 'Refreshing…' : 'Refresh news'}
          </button>
        </div>

        {error && <ErrorBox message={error} retry={() => void load()} />}
        {refreshError && <ErrorBox message={refreshError} />}
        {data?.error && (
          <div className="notice error" role="alert">
            {data.error}
          </div>
        )}
        {!data && !error && <Loading />}

        {data && (
          <>
            <div className="rss-category-bar" role="group" aria-label="News industry categories">
              {data.categories.map((entry) => (
                <button
                  key={entry.key}
                  type="button"
                  className={`rss-category ${entry.key === category ? 'selected' : ''}`}
                  aria-pressed={entry.key === category}
                  onClick={() => chooseCategory(entry.key)}
                >
                  {entry.name}
                  <span>{entry.count}</span>
                </button>
              ))}
            </div>

            <RSSHighlights
              key={category}
              category={category}
              hasNews={data.items.length > 0}
              newsRevision={data.last_refreshed}
            />

            {data.items.length === 0 ? (
              <Empty>
                {data.refreshing
                  ? 'Fetching RSS headlines…'
                  : 'No recent English headlines in this category.'}
              </Empty>
            ) : (
              <div className="rss-articles">
                {data.items.map((article) => (
                  <article className="rss-compact-row" key={`${category}-${article.source_url}`}>
                    <time className="rss-compact-date" dateTime={article.published_at}>
                      {article.published_at.slice(0, 10)}
                    </time>
                    <span className="rss-compact-source" title={article.source_name}>
                      {article.source_name}
                    </span>
                    <a
                      className="rss-compact-title"
                      href={article.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      {article.headline}
                    </a>
                  </article>
                ))}
              </div>
            )}
          </>
        )}
      </section>

      {/* Scoped styling for the compact news rows */}
      <style>{`
        .rss-articles .rss-compact-row {
          display: grid;
          grid-template-columns: 105px 145px minmax(0, 1fr);
          column-gap: 16px;
          align-items: baseline;
          padding: 12px 0;
          border-bottom: 1px solid var(--border);
        }

        .rss-compact-date,
        .rss-compact-source {
          color: var(--muted);
          font-size: 0.82rem;
        }

        .rss-compact-source {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .rss-articles .rss-compact-title {
          display: block;
          min-width: 0;
          color: inherit;
          font-size: 0.94rem;
          font-weight: 500;
          line-height: 1.5;
          text-decoration: none;
          overflow-wrap: anywhere;
        }

        .rss-articles .rss-compact-title:hover {
          color: var(--accent);
          text-decoration: underline;
        }

        @media (max-width: 700px) {
          .rss-articles .rss-compact-row {
            grid-template-columns: 105px minmax(0, 1fr);
            row-gap: 5px;
          }

          .rss-articles .rss-compact-title {
            grid-column: 1 / -1;
          }
        }
      `}</style>
    </>
  );
}
