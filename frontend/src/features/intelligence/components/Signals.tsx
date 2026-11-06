import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge } from '../../../shared/ui/Presentation';
import { dateTime, formatNumber } from '../../../shared/utils/format';
import { intelligenceApi } from '../api';

export function Signals() {
  const signals = useResource(() => intelligenceApi.signals());
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
