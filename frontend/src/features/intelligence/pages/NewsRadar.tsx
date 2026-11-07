import { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';

import { EvidenceTable } from '../../../shared/ui/EvidenceTable';
import { Empty, ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { PageTitle } from '../../../shared/ui/Presentation';
import { dateTime } from '../../../shared/utils/format';
import type { ChatReply } from '../../research/types';
import { intelligenceApi } from '../api';
import type { RSSNewsResponse } from '../types';

export function NewsRadar() {
  const [category, setCategory] = useState('ai');
  const activeCategory = useRef('ai');

  const [data, setData] = useState<RSSNewsResponse>();
  const [error, setError] = useState('');
  const [refreshError, setRefreshError] = useState('');
  const [refreshingRequest, setRefreshingRequest] = useState(false);

  const [summary, setSummary] = useState<ChatReply>();
  const [summaryError, setSummaryError] = useState('');
  const [summarizing, setSummarizing] = useState(false);

  // Load cached news from the backend.
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

  // Poll while the background RSS collection is running.
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

  // Only this action invokes the configured LLM.
  async function highlights() {
    const selectedCategory = category;

    setSummarizing(true);
    setSummary(undefined);
    setSummaryError('');

    try {
      const result = await intelligenceApi.rssHighlights(selectedCategory);

      if (activeCategory.current === selectedCategory) {
        setSummary(result);
      }
    } catch (err) {
      if (activeCategory.current === selectedCategory) {
        setSummaryError(err instanceof Error ? err.message : 'AI highlights unavailable');
      }
    } finally {
      setSummarizing(false);
    }
  }

  function chooseCategory(next: string) {
    if (next === category) return;

    activeCategory.current = next;
    setCategory(next);
    setData(undefined);
    setError('');
    setSummary(undefined);
    setSummaryError('');
  }

  return (
    <>
      <PageTitle title="Industry intelligence" />

      <section className="panel">
        {/* Page header */}
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
            {/* Industry category filters */}
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

            {/* Optional AI highlights */}
            <div className="rss-highlights">
              <div>
                <h3>Industry highlights</h3>
                <small>
                  Generate AI highlights from the selected industry's news. Full articles are not retrieved.
                </small>
              </div>

              <button
                type="button"
                className="button"
                disabled={summarizing || data.items.length === 0}
                onClick={() => void highlights()}
              >
                {summarizing ? 'Generating…' : 'Generate AI highlights'}
              </button>
            </div>

            {summaryError && <ErrorBox message={summaryError} />}

            {summary && (
              <section className="chat-answer">
                <div className="markdown">
                  <ReactMarkdown>{summary.answer}</ReactMarkdown>
                </div>

                <Gaps gaps={summary.gaps} />

                <details>
                  <summary>Supporting news sources</summary>
                  <EvidenceTable evidence={summary.evidence} />
                </details>
              </section>
            )}

            {/* Compact news list */}
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
