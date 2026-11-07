import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, SourceLink } from '../../../shared/ui/Presentation';
import { marketApi } from '../api';
import {
  calendarDate,
  earningsAmount,
  earningsEPS,
  earningsPercent,
  earningsTiming,
  surpriseClass,
} from '../earningsFormat';
import type { EarningsRecord, EarningsResponse, UpcomingEarnings } from '../types';

const basis = (value: EarningsRecord['actual_basis']) => {
  if (value === 'adjusted') return 'Vendor adjusted / non-GAAP';
  if (value === 'gaap_diluted') return 'GAAP diluted';
  if (value === 'gaap_basic') return 'GAAP basic';
  return 'Basis unavailable';
};

function Preview({ upcoming, currency }: { upcoming: UpcomingEarnings | null; currency: 'USD' | 'CAD' }) {
  if (!upcoming) {
    return (
      <div className="earnings-preview-unavailable">
        <strong>No upcoming earnings date available</strong>
        <p className="muted">
          The provider did not return a dated upcoming announcement in the requested window.
        </p>
      </div>
    );
  }
  return (
    <div className="earnings-preview" aria-label="Upcoming earnings preview">
      <div className="earnings-preview-date">
        <span className="earnings-kicker">
          Upcoming earnings · {upcoming.date_status === 'confirmed' ? 'Confirmed' : 'Vendor estimate'}
        </span>
        <strong>{calendarDate(upcoming.scheduled_date)}</strong>
        <small>
          {upcoming.fiscal_quarter && upcoming.fiscal_year
            ? `${upcoming.fiscal_quarter} FY${upcoming.fiscal_year} · `
            : ''}
          {earningsTiming(upcoming.timing)}
        </small>
      </div>
      <div className="earnings-preview-estimates">
        <div>
          <span className="muted">EPS estimate</span>
          <strong>{earningsEPS(upcoming.eps_estimate, currency)}</strong>
          <small>
            {upcoming.eps_estimate_basis === 'adjusted' ? 'Vendor adjusted / non-GAAP' : 'Basis unverified'}
          </small>
        </div>
        <div>
          <span className="muted">Revenue estimate</span>
          <strong>{earningsAmount(upcoming.revenue_estimate, currency)}</strong>
          <small>Vendor consensus, if available</small>
        </div>
      </div>
      <small className="earnings-warning">
        Calendar dates and session timing are vendor-provided, not verified issuer release timestamps.
      </small>
    </div>
  );
}

function Review({ response }: { response: EarningsResponse }) {
  if (!response.history.length) {
    return (
      <div className="earnings-no-history">
        <h3>Historical earnings review</h3>
        <Empty>No dated earnings results returned in the provider's current calendar window.</Empty>
      </div>
    );
  }
  return (
    <div className="earnings-review">
      <div className="earnings-review-heading">
        <h3>Historical earnings review</h3>
        <span className="muted">{response.history.length} dated result(s) · latest first</span>
      </div>
      <div className="table-scroll earnings-table">
        <table>
          <caption className="sr-only">
            Earnings calendar dates, EPS actual and estimates, revenue actual and estimates, and calculated
            surprises
          </caption>
          <thead>
            <tr>
              <th>Calendar date</th>
              <th>Fiscal period</th>
              <th>EPS actual</th>
              <th>EPS estimate</th>
              <th>EPS surprise</th>
              <th>Revenue actual</th>
              <th>Revenue estimate</th>
              <th>Revenue surprise</th>
            </tr>
          </thead>
          <tbody>
            {response.history.map((record) => (
              <tr key={record.event_id}>
                <td>{calendarDate(record.reported_on)}</td>
                <td>
                  {record.fiscal_quarter} FY{record.fiscal_year}
                </td>
                <td>
                  {earningsEPS(record.actual_eps, response.currency)}
                  {record.actual_eps !== null && <small>{basis(record.actual_basis)}</small>}
                </td>
                <td>{earningsEPS(record.estimate_eps, response.currency)}</td>
                <td className={surpriseClass(record.surprise_pct)}>{earningsPercent(record.surprise_pct)}</td>
                <td>{earningsAmount(record.actual_revenue, response.currency)}</td>
                <td>{earningsAmount(record.estimate_revenue, response.currency)}</td>
                <td className={surpriseClass(record.revenue_surprise_pct)}>
                  {earningsPercent(record.revenue_surprise_pct)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <small className="earnings-warning">
        Calendar dates are not verified first-public release times. Surprise percentages are supplied by the
        backend using comparable vendor fields; no stock-price reaction is inferred.
      </small>
    </div>
  );
}

function EarningsContent({ response }: { response: EarningsResponse }) {
  return (
    <>
      <Preview upcoming={response.upcoming} currency={response.currency} />
      <Review response={response} />
      {response.sources.length > 0 && (
        <p className="earnings-sources">
          Source:{' '}
          {response.sources.map((source, index) => (
            <span key={`${source.url}:${index}`}>
              {index > 0 ? ', ' : ''}
              <SourceLink url={source.url} name={source.name} />
              {source.fixture ? ' · SYNTHETIC' : ''}
              {source.cached ? ' · cached' : ''}
              {' · Retrieved '}
              {new Date(source.fetched_at).toLocaleString('en-US', { timeZone: 'UTC' })}
              {' UTC'}
            </span>
          ))}
        </p>
      )}
      {response.gaps.length > 0 && (
        <details className="earnings-gaps">
          <summary>Coverage and interpretation limits ({response.gaps.length})</summary>
          <ul>
            {response.gaps.map((gap, index) => (
              <li key={`${index}:${gap}`}>{gap}</li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}

export function EarningsPanel({ symbol }: { symbol: string }) {
  const request = useResource(() => marketApi.earnings(symbol), [symbol]);
  return (
    <section className="panel earnings-panel" aria-label="Earnings preview and review">
      <div className="panel-heading">
        <h2>Earnings · Preview &amp; Review</h2>
        {request.data && <ModeBadge mode={request.data.mode} />}
      </div>
      {request.loading ? (
        <Loading />
      ) : request.error ? (
        <ErrorBox message={request.error} retry={request.reload} />
      ) : request.data ? (
        <EarningsContent response={request.data} />
      ) : (
        <Empty>Earnings calendar unavailable.</Empty>
      )}
    </section>
  );
}
