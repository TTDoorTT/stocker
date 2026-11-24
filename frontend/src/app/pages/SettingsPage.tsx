import { useResource } from '../../shared/hooks/useResource';
import { ErrorBox, Loading } from '../../shared/ui/Feedback';
import { ModeBadge, PageTitle } from '../../shared/ui/Presentation';
import { appApi } from '../api';
import { AIForm } from '../components/AIConfiguration';

export function Settings() {
  const ai = useResource(appApi.ai);
  const health = useResource(appApi.health);
  return (
    <>
      <PageTitle title="Settings / AI" />
      <div className="settings-stack">
        <section className="panel" aria-label="Local connection status">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">ENVIRONMENT &amp; RUNTIME</p>
              <h2>Local connection status</h2>
            </div>
            {health.data && <ModeBadge mode={health.data.mode} />}
          </div>
          {health.loading ? (
            <Loading />
          ) : health.error ? (
            <ErrorBox message={health.error} retry={health.reload} />
          ) : (
            health.data && (
              <>
                <div className="settings-status-grid">
                  <div className="settings-stat">
                    <span className="muted">API</span>
                    <strong>{health.data.status}</strong>
                  </div>
                  <div className="settings-stat">
                    <span className="muted">Data mode</span>
                    <div>
                      <ModeBadge mode={health.data.mode} />
                    </div>
                  </div>
                  <div className="settings-stat">
                    <span className="muted">Active model</span>
                    <code>{health.data.model_id || 'Not configured'}</code>
                  </div>
                  <div className="settings-stat">
                    <span className="muted">Live model configured</span>
                    <strong>{health.data.model_configured ? 'Yes' : 'No'}</strong>
                  </div>
                </div>
                {!!health.data.missing_configuration?.length && (
                  <div className="notice settings-missing">
                    <strong>Unavailable optional integrations / settings:</strong>{' '}
                    {health.data.missing_configuration.join(', ')}
                  </div>
                )}
              </>
            )
          )}
        </section>

        <section className="panel" aria-label="AI configuration">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">MODEL CONNECTION</p>
              <h2>AI configuration</h2>
            </div>
            {ai.data && (
              <div className="actions">
                <span className="badge">Source: {ai.data.source}</span>
                <span className="badge">API key: {ai.data.has_api_key ? 'Saved' : 'None'}</span>
              </div>
            )}
          </div>
          {ai.loading ? (
            <Loading />
          ) : ai.error ? (
            <ErrorBox message={ai.error} retry={ai.reload} />
          ) : (
            ai.data && (
              <AIForm
                key={`${ai.data.source}:${ai.data.base_url}:${ai.data.model_id}`}
                initial={ai.data}
                onSaved={() => {
                  ai.reload();
                  health.reload();
                }}
              />
            )
          )}
        </section>

        <section className="panel" aria-label="Market coverage">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">DATA PROVIDERS</p>
              <h2>Market coverage</h2>
            </div>
          </div>
          <div className="settings-coverage-grid">
            <div className="settings-coverage-card">
              <h3>United States</h3>
              <p className="muted">
                United States · initial AAPL, MSFT and NVDA coverage. Provider availability varies by ticker.
              </p>
            </div>
            <div className="settings-coverage-card">
              <h3>Canada · TSX / TSXV</h3>
              <p className="muted">
                Canada / TSX and TSXV: optional daily history and Bank of Canada macro. Canadian statements
                and Finnhub quotes are unavailable.
              </p>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
