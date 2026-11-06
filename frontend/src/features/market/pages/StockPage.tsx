import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { EvidenceTable } from '../../../shared/ui/EvidenceTable';
import { Empty, ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, PageTitle, SourceLink } from '../../../shared/ui/Presentation';
import { dateTime, money } from '../../../shared/utils/format';
import { portfolioApi } from '../../portfolio/api';
import { researchApi } from '../../research/api';
import { Chat } from '../../research/components/Chat';
import { marketApi } from '../api';
import { PriceChart } from '../components/PriceChart';
export function StockPage() {
  const { symbol = 'AAPL' } = useParams();
  const stock = useResource(() => marketApi.stock(symbol), [symbol]);
  const history = useResource(() => marketApi.history(symbol), [symbol]);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');
  const navigate = useNavigate();
  async function research() {
    setBusy(true);
    setActionError('');
    try {
      const run = await researchApi.runResearch(symbol);
      navigate(`/runs/${run.run_id}`);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Research unavailable');
    } finally {
      setBusy(false);
    }
  }
  async function watch() {
    try {
      await portfolioApi.watch(symbol);
      setNotice(`${symbol} added to watchlist`);
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Could not add stock');
    }
  }
  if (stock.loading) return <Loading />;
  if (stock.error) return <ErrorBox message={stock.error} retry={stock.reload} />;
  if (!stock.data) return <Empty>Stock unavailable.</Empty>;
  const data = stock.data;
  return (
    <>
      <PageTitle eyebrow={`${data.market} / COMPANY RESEARCH`} title={data.name || data.symbol}>
        <ModeBadge mode={data.mode} />
      </PageTitle>
      <div className="stock-header panel">
        <div>
          <span className="stock-symbol">{data.symbol}</span>
          <span className="muted">
            {' '}
            {data.market} · {data.currency}
          </span>
          <div className="quote-price">{money(data.quote?.price, data.currency)}</div>
          {data.quote ? (
            <p className="source">
              <SourceLink url={data.quote.source_url} name={data.quote.source_name} /> ·{' '}
              {dateTime(data.quote.timestamp)} · {data.quote.stale ? 'stale' : 'provider timestamp'}
              {data.quote.delayed ? ' · delayed' : ''}
              {data.quote.cached ? ' · cached' : ''}
              {data.quote.fetched_at && <> · Retrieved {dateTime(data.quote.fetched_at)}</>}
            </p>
          ) : (
            <p className="muted">Quote unavailable</p>
          )}
        </div>
        <div className="actions">
          <button className="button secondary" onClick={watch}>
            + Watchlist
          </button>
          <button className="button" onClick={research} disabled={busy}>
            {busy ? 'Starting…' : 'Run Research'} <span>↗</span>
          </button>
        </div>
      </div>
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      {actionError && <ErrorBox message={actionError} />}
      <Gaps gaps={data.gaps} />
      <section className="panel">
        <div className="panel-heading">
          <h2>Company overview</h2>
          <span className="badge">Source context</span>
        </div>
        <p>{data.profile || 'Company description unavailable.'}</p>
        {data.evidence
          ?.filter((ev) => typeof ev.value === 'string')
          .slice(0, 3)
          .map((ev) => (
            <small key={ev.evidence_id}>
              <SourceLink url={ev.source_url} name={ev.source_name} /> · Retrieved {dateTime(ev.fetched_at)}
            </small>
          ))}
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h2>Price history</h2>
          <ModeBadge mode={data.mode} />
        </div>
        {history.loading ? (
          <Loading />
        ) : history.error ? (
          <ErrorBox message={history.error} />
        ) : (
          <PriceChart bars={history.data || []} currency={data.currency} />
        )}
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h2>Financial facts</h2>
          <span className="muted">Fiscal periods retained</span>
        </div>
        <EvidenceTable evidence={data.facts} />
      </section>
      <Chat key={symbol} symbol={symbol} />
      <section className="panel">
        <h2>Recent filings & news</h2>
        {data.news?.length ? (
          <div className="news-list">
            {data.news.map((item, i) => (
              <article key={i}>
                <a href={item.source_url} target="_blank" rel="noreferrer">
                  {item.headline} ↗
                </a>
                <small>
                  {item.source_name} · {dateTime(item.published_at)}
                </small>
              </article>
            ))}
          </div>
        ) : (
          <Empty>No recent news or filing references available.</Empty>
        )}
      </section>
      <Link to="/research">← Back to research</Link>
    </>
  );
}
