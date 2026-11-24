import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { EvidenceTable } from '../../../shared/ui/EvidenceTable';
import { Empty, ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, PageTitle, SourceLink } from '../../../shared/ui/Presentation';
import { dateTime, money } from '../../../shared/utils/format';
import { portfolioApi } from '../../portfolio/api';
import { Chat } from '../../research/components/Chat';
import { DeepResearchPanel } from '../../research/components/DeepResearchPanel';
import { marketApi } from '../api';
import { PriceHistoryPanel } from '../components/PriceHistoryPanel';
import { QuarterlyTrendsPanel } from '../components/QuarterlyTrendsPanel';
import { StockQuickSearch } from '../components/StockQuickSearch';

type StockTab = 'overview' | 'deep-research';

export function StockPage() {
  const { symbol = 'AAPL' } = useParams();
  const stock = useResource(() => marketApi.stock(symbol), [symbol]);
  const [selectedTab, setSelectedTab] = useState<{ symbol: string; tab: StockTab } | null>(null);
  const [actionError, setActionError] = useState('');
  const [notice, setNotice] = useState('');

  const activeTab: StockTab = selectedTab?.symbol === symbol ? selectedTab.tab : 'overview';

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
      <StockQuickSearch key={`switch-${symbol}`} />
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
          <button type="button" className="button secondary" onClick={() => void watch()}>
            + Watchlist
          </button>
        </div>
      </div>
      <div className="actions stock-tabs" role="tablist" aria-label="Stock workspace views">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'overview'}
          className={`button ${activeTab === 'overview' ? '' : 'secondary'}`}
          onClick={() => setSelectedTab({ symbol, tab: 'overview' })}
        >
          Overview
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'deep-research'}
          className={`button ${activeTab === 'deep-research' ? '' : 'secondary'}`}
          onClick={() => setSelectedTab({ symbol, tab: 'deep-research' })}
        >
          Deep Research
        </button>
      </div>
      {notice && (
        <p role="status" className="notice">
          {notice}
        </p>
      )}
      {actionError && <ErrorBox message={actionError} />}
      {activeTab === 'overview' ? (
        <>
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
                  <SourceLink url={ev.source_url} name={ev.source_name} /> · Retrieved{' '}
                  {dateTime(ev.fetched_at)}
                </small>
              ))}
          </section>
          <PriceHistoryPanel key={`price-${symbol}`} symbol={symbol} mode={data.mode} />
          <QuarterlyTrendsPanel key={`quarterly-${symbol}`} symbol={symbol} />
          <Chat key={`chat-${symbol}`} symbol={symbol} />
          <section className="panel" aria-label="Financial facts">
            <div className="panel-heading">
              <h2>Financial facts</h2>
              <span className="muted">Fiscal periods retained</span>
            </div>
            <div className="bounded-panel-body">
              <EvidenceTable evidence={data.facts} />
            </div>
          </section>
          <section className="panel" aria-label="Recent filings and news">
            <div className="panel-heading">
              <h2>Recent filings &amp; news</h2>
              <span className="muted">{data.news?.length || 0} item(s)</span>
            </div>
            {data.news?.length ? (
              <div className="bounded-panel-body news-list">
                {data.news.map((item, i) => (
                  <article key={`${item.source_url}-${i}`}>
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
        </>
      ) : (
        <DeepResearchPanel key={`deep-${symbol}`} symbol={symbol} />
      )}
      <Link to="/research">← Back to research</Link>
    </>
  );
}
