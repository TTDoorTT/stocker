import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Link, useNavigate } from 'react-router-dom';
import { intelligenceApi } from '../features/intelligence/api';
import { researchApi } from '../features/research/api';
import { request } from '../shared/api/client';
import { useResource } from '../shared/hooks/useResource';
import type { ChatReply, Mode, NewsItem, Quote } from '../shared/types/index';
import { EvidenceTable } from '../shared/ui/EvidenceTable';
import { Empty, ErrorBox, Gaps, Loading } from '../shared/ui/Feedback';
import { ModeBadge, PageTitle, SourceLink } from '../shared/ui/Presentation';
import { dateTime, formatNumber, money } from '../shared/utils/format';

function NewsList({ items }: { items: NewsItem[] }) {
  return items.length ? (
    <div className="news-list">
      {items.map((item, i) => (
        <article key={i}>
          <SourceLink url={item.source_url} name={item.headline} />
          <small>
            {item.source_name} · {dateTime(item.published_at)}
            {item.symbols?.length ? ` · ${item.symbols.join(', ')}` : ''}
            {item.cached ? ' · cached' : ''}
          </small>
          {item.fetched_at && <small>Retrieved {dateTime(item.fetched_at)}</small>}
          {item.summary && <p>{item.summary}</p>}
        </article>
      ))}
    </div>
  ) : (
    <Empty>No headlines available from configured sources.</Empty>
  );
}
export function NewsRadar() {
  const news = useResource(intelligenceApi.news);
  const [summary, setSummary] = useState<ChatReply>();
  const [summaryError, setSummaryError] = useState('');
  const [summarizing, setSummarizing] = useState(false);
  async function summarize() {
    setSummarizing(true);
    setSummaryError('');
    setSummary(undefined);
    try {
      setSummary(await intelligenceApi.summarizeNews());
    } catch (error) {
      setSummaryError(error instanceof Error ? error.message : 'Headline summary unavailable');
    } finally {
      setSummarizing(false);
    }
  }
  return (
    <>
      <PageTitle title="Industry intelligence" />
      <section className="panel">
        <h2>News radar</h2>
        <p className="muted">
          Headlines and filings remain linked to their original source. Unavailable coverage is shown
          explicitly.
        </p>
        {news.loading ? (
          <Loading />
        ) : news.error ? (
          <ErrorBox message={news.error} retry={news.reload} />
        ) : (
          news.data && (
            <>
              <NewsList items={news.data.items} />
              <Gaps gaps={news.data.gaps} />
              <small>Retrieved {dateTime(news.data.fetched_at)}</small>
              {news.data.mode === 'live' && news.data.items.length > 0 && (
                <div>
                  <p className="muted">
                    Optional AI summary covers retrieved headlines only; full article text is not available.
                  </p>
                  <button className="button secondary" onClick={summarize} disabled={summarizing}>
                    {summarizing ? 'Summarizing sourced headlines…' : 'Summarize headlines'}
                  </button>
                </div>
              )}
            </>
          )
        )}
        {summaryError && <ErrorBox message={summaryError} />}{' '}
        {summary && (
          <section className="chat-answer">
            <h3>Headline-only summary</h3>
            <ModeBadge mode={summary.mode} />
            <div className="markdown">
              <ReactMarkdown>{summary.answer}</ReactMarkdown>
            </div>
            <Gaps gaps={summary.gaps} />
            <details>
              <summary>Summary sources</summary>
              <EvidenceTable evidence={summary.evidence} />
            </details>
          </section>
        )}
      </section>
      <Signals />
    </>
  );
}

interface Signal {
  series_id: string;
  name: string;
  value: number | null;
  unit: string;
  observation_date?: string;
  source_url: string;
  source_name: string;
  fetched_at: string;
  stale: boolean;
  status: string;
  observations: { date: string; value: number }[];
  gaps: string[];
}
function Signals() {
  const signals = useResource(() =>
    request<{ mode: Mode; items: Signal[]; gaps: string[] }>('/intelligence/signals'),
  );
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Industry signals</h2>
        {signals.data && <ModeBadge mode={signals.data.mode} />}
      </div>
      {signals.loading ? (
        <Loading />
      ) : signals.error ? (
        <ErrorBox message={signals.error} retry={signals.reload} />
      ) : (
        signals.data && (
          <>
            <Gaps gaps={signals.data.gaps} />
            {signals.data.items.length ? (
              <div className="signal-grid">
                {signals.data.items.map((signal) => (
                  <article key={signal.series_id}>
                    <h3>{signal.name}</h3>
                    <strong className="quote-price">
                      {signal.value === null ? 'Unavailable' : `${formatNumber(signal.value)} ${signal.unit}`}
                    </strong>
                    <small>
                      Observation: {signal.observation_date || 'Unavailable'} ·{' '}
                      {signal.stale ? 'stale' : signal.status}
                    </small>
                    <a href={signal.source_url} target="_blank" rel="noreferrer">
                      {signal.source_name} ↗
                    </a>
                    <small>Retrieved {dateTime(signal.fetched_at)}</small>
                    <Gaps gaps={signal.gaps} />
                    {signal.observations.length > 1 && (
                      <details>
                        <summary>Observation series</summary>
                        <div className="table-scroll">
                          <table>
                            <thead>
                              <tr>
                                <th>Date</th>
                                <th>{signal.unit}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {signal.observations.map((value) => (
                                <tr key={value.date}>
                                  <td>{value.date}</td>
                                  <td>{formatNumber(value.value)}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </details>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <Empty>Signals unavailable. Configure an authorized source to retrieve observations.</Empty>
            )}
          </>
        )
      )}
    </section>
  );
}
interface Review {
  mode: Mode;
  as_of: string;
  proxies: {
    symbol: string;
    name: string;
    quote: Quote | null;
    daily_return_pct: number | null;
    gaps: string[];
  }[];
  news: NewsItem[];
  gaps: string[];
  session: string;
  coverage: string;
}
export function DailyReview() {
  const review = useResource(() => request<Review>('/daily-review'));
  return (
    <>
      <PageTitle title="Daily market review" />
      {review.loading ? (
        <Loading />
      ) : review.error ? (
        <ErrorBox message={review.error} retry={review.reload} />
      ) : review.data ? (
        <>
          <section className="panel">
            <div className="panel-heading">
              <h2>Available market context</h2>
              <ModeBadge mode={review.data.mode} />
            </div>
            <p>{review.data.coverage}</p>
            <p className="muted">
              {review.data.session} · As of {dateTime(review.data.as_of)}
            </p>
            <Gaps gaps={review.data.gaps} />
          </section>
          <div className="market-grid">
            {review.data.proxies.map((proxy) => (
              <article className="panel market-card" key={proxy.symbol}>
                <div className="row">
                  <Link to={`/stocks/${proxy.symbol}`}>
                    <strong>{proxy.symbol} ↗</strong>
                  </Link>
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
                    : `${formatNumber(proxy.daily_return_pct)}% daily return`}
                </p>
                {proxy.quote && (
                  <>
                    <SourceLink
                      className="source"
                      url={proxy.quote.source_url}
                      name={proxy.quote.source_name}
                    />
                    <small>
                      {dateTime(proxy.quote.timestamp)} · {proxy.quote.stale ? 'stale' : 'provider timestamp'}
                      {proxy.quote.cached ? ' · cached' : ''}
                    </small>
                  </>
                )}
                <Gaps gaps={proxy.gaps} />
              </article>
            ))}
          </div>
          <section className="panel">
            <h2>Headlines & filings</h2>
            <NewsList items={review.data.news} />
          </section>
        </>
      ) : (
        <Empty>Market review unavailable.</Empty>
      )}
    </>
  );
}
interface Industry {
  slug: string;
  name: string;
  prompt: string;
  symbols: string[];
  gaps: string[];
}
export function Industries() {
  const industries = useResource(() => request<Industry[]>('/industries'));
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();
  async function start(industry: Industry, symbol: string) {
    setBusy(`${industry.slug}-${symbol}`);
    setError('');
    try {
      const run = await researchApi.runResearch(symbol, industry.slug);
      navigate(`/runs/${run.run_id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Research could not start');
    } finally {
      setBusy('');
    }
  }
  return (
    <>
      <PageTitle title="Industry research" />
      <p className="muted">
        Guided industry templates organize questions and evidence needs. Launching a representative company
        analysis reuses the six-stage pipeline; it is not comprehensive sector coverage.
      </p>
      {error && <ErrorBox message={error} />}{' '}
      {industries.loading ? (
        <Loading />
      ) : industries.error ? (
        <ErrorBox message={industries.error} retry={industries.reload} />
      ) : industries.data?.length ? (
        <div className="industry-grid">
          {industries.data.map((industry) => (
            <article className="panel" key={industry.slug}>
              <p className="eyebrow">GUIDED TEMPLATE</p>
              <h2>{industry.name}</h2>
              <details>
                <summary>Open research questions</summary>
                <p>{industry.prompt}</p>
                <Gaps gaps={industry.gaps} />
                <p className="muted">Representative U.S. company research</p>
                <div className="actions">
                  {industry.symbols.map((symbol) => (
                    <button
                      className="button secondary"
                      key={symbol}
                      disabled={!!busy}
                      onClick={() => start(industry, symbol)}
                    >
                      {busy === `${industry.slug}-${symbol}` ? 'Starting…' : `Research ${symbol} ↗`}
                    </button>
                  ))}
                </div>
              </details>
            </article>
          ))}
        </div>
      ) : (
        <Empty>Industry templates are unavailable.</Empty>
      )}
    </>
  );
}
