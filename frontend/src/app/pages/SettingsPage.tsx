import { useResource } from '../../shared/hooks/useResource';
import { ErrorBox, Loading } from '../../shared/ui/Feedback';
import { ModeBadge, PageTitle } from '../../shared/ui/Presentation';
import { appApi } from '../api';
export function Settings() {
  const health = useResource(appApi.health);
  return (
    <>
      <PageTitle title="Settings / AI" />
      <section className="panel">
        <h2>Local connection status</h2>
        {health.loading ? (
          <Loading />
        ) : health.error ? (
          <ErrorBox message={health.error} retry={health.reload} />
        ) : (
          health.data && (
            <>
              <p>
                API: <strong>{health.data.status}</strong>
              </p>
              <p>
                Data mode: <ModeBadge mode={health.data.mode} />
              </p>
              <p>
                Model: <strong>{health.data.model_id || 'Not configured'}</strong>
              </p>
              <p>
                Live model configured: <strong>{health.data.model_configured ? 'Yes' : 'No'}</strong>
              </p>
              {health.data.missing_configuration?.length && (
                <p>
                  Unavailable optional integrations / settings: {health.data.missing_configuration.join(', ')}
                </p>
              )}
            </>
          )
        )}
        <div className="notice">
          Provider credentials are configured in the backend environment. Keys are never entered or exposed in
          this browser. Fixture mode uses a deterministic model stub and synthetic financial samples.
        </div>
        <h3>Market coverage</h3>
        <p>United States · initial AAPL, MSFT and NVDA coverage. Provider availability varies by ticker.</p>
        <p className="muted">
          Canada / TSX and TSXV: optional daily history and Bank of Canada macro. Canadian statements and
          Finnhub quotes are unavailable.
        </p>
      </section>
    </>
  );
}
