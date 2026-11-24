import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, PageTitle, SourceLink } from '../../../shared/ui/Presentation';
import { dateTime } from '../../../shared/utils/format';
import { intelligenceApi } from '../../intelligence/api';
import { portfolioApi } from '../../portfolio/api';
import { Heatmap } from '../components/Heatmap';
import { MarketCards } from '../components/MarketCards';

const COMPACT_HEADLINE_LIMIT = 5;

export function Home() {
  const review = useResource(intelligenceApi.dailyReview);
  const watchlist = useResource(portfolioApi.watchlist);
  const [showAllNews, setShowAllNews] = useState(false);

  const news = review.data?.news ?? [];
  const visibleNews = showAllNews ? news : news.slice(0, COMPACT_HEADLINE_LIMIT);

  return (
    <>
      <PageTitle title="Market workspace">
        <div className="actions">
          {review.data && <ModeBadge mode={review.data.mode} />}
          <span className="badge">United States</span>
        </div>
      </PageTitle>
      <div className="section-title">
        <h2>Market overview</h2>
        <p className="muted">
          {review.data
            ? `${review.data.coverage} · As of ${dateTime(review.data.as_of)}`
            : 'Liquid ETF prices as market proxies; these are not index levels.'}
        </p>
      </div>
      {review.loading ? (
        <Loading />
      ) : review.error ? (
        <ErrorBox message={review.error} retry={review.reload} />
      ) : review.data?.proxies?.length ? (
        <>
          <MarketCards proxies={review.data.proxies} mode={review.data.mode} />
          {review.data.gaps.length > 0 && (
            <details className="home-coverage-details">
              <summary>Market coverage limitations ({review.data.gaps.length})</summary>
              <Gaps gaps={review.data.gaps} />
            </details>
          )}
        </>
      ) : (
        <Empty>Market quotes unavailable.</Empty>
      )}
      <Heatmap />
      <section className="panel" aria-label="Top news">
        <div className="panel-heading">
          <div>
            <h2>Top News</h2>
            <small>
              {news.length > 0
                ? `Showing ${visibleNews.length} of ${news.length} recent headline(s)`
                : 'Recent company news and filing references'}
            </small>
          </div>
          {news.length > COMPACT_HEADLINE_LIMIT && (
            <button
              type="button"
              className="link-button"
              onClick={() => setShowAllNews((expanded) => !expanded)}
            >
              {showAllNews ? 'Show fewer' : `Show all (${news.length})`}
            </button>
          )}
        </div>
        {review.loading ? (
          <Loading />
        ) : review.error ? (
          <ErrorBox message={review.error} retry={review.reload} />
        ) : visibleNews.length ? (
          <div className="home-headlines-window">
            {visibleNews.map((item, index) => (
              <article className="home-headline-row" key={`${item.source_url}-${index}`}>
                <SourceLink url={item.source_url} name={item.headline} />
                <small>
                  {item.source_name} · {dateTime(item.published_at)}
                  {item.symbols?.length ? ` · ${item.symbols.join(', ')}` : ''}
                  {item.cached ? ' · cached' : ''}
                </small>
              </article>
            ))}
          </div>
        ) : (
          <Empty>No headlines available from configured sources.</Empty>
        )}
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h2>Your watchlist</h2>
          <Link to="/my-stocks">Manage stocks ↗</Link>
        </div>
        {watchlist.loading ? (
          <Loading />
        ) : watchlist.error ? (
          <ErrorBox message={watchlist.error} />
        ) : watchlist.data?.length ? (
          <div className="ticker-links">
            {watchlist.data.map(({ symbol }) => (
              <Link key={symbol} to={`/stocks/${symbol}`}>
                {symbol} ↗
              </Link>
            ))}
          </div>
        ) : (
          <Empty>Add a stock from its overview page to keep it close.</Empty>
        )}
      </section>
    </>
  );
}
