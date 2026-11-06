import { Link } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, PageTitle, SourceLink } from '../../../shared/ui/Presentation';
import { dateTime, formatNumber, money } from '../../../shared/utils/format';
import { intelligenceApi } from '../api';
import { NewsList } from '../components/NewsList';
export function DailyReview() {
  const review = useResource(() => intelligenceApi.dailyReview());
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
