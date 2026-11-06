import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { PageTitle } from '../../../shared/ui/Presentation';
import { researchApi } from '../../research/api';
import { intelligenceApi } from '../api';
import type { Industry } from '../types';

export function Industries() {
  const industries = useResource(() => intelligenceApi.industries());
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
