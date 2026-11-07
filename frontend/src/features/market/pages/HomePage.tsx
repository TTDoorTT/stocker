import { Link } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Loading } from '../../../shared/ui/Feedback';
import { PageTitle } from '../../../shared/ui/Presentation';
import { portfolioApi } from '../../portfolio/api';
import { PositionsPreview } from '../../portfolio/components/PositionsPreview';
import { marketApi } from '../api';
import { Heatmap } from '../components/Heatmap';
import { MarketCards } from '../components/MarketCards';
export function Home() {
  const overview = useResource(marketApi.overview);
  const watchlist = useResource(portfolioApi.watchlist);
  return (
    <>
      <PageTitle title="Market workspace">
        <span className="badge">United States</span>
      </PageTitle>
      <div className="section-title">
        <h2>Market overview</h2>
        <p className="muted">Liquid ETF prices as market proxies; these are not index levels.</p>
      </div>
      {overview.loading ? (
        <Loading />
      ) : overview.error ? (
        <ErrorBox message={overview.error} retry={overview.reload} />
      ) : overview.data?.length ? (
        <MarketCards stocks={overview.data} />
      ) : (
        <Empty>Market quotes unavailable.</Empty>
      )}
      <Heatmap />
      <PositionsPreview />
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
