import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { PageTitle } from '../../../shared/ui/Presentation';
import { researchApi } from '../../research/api';
import { intelligenceApi } from '../api';
import { FilingExcerpts } from '../components/FilingExcerpts';
import { IndustryEvidence } from '../components/IndustryEvidence';
import { IndustrySection } from '../components/IndustrySection';
import type { IndustrySectionKey } from '../types';

const sections: { id: IndustrySectionKey; label: string }[] = [
  { id: 'overview', label: 'Overview' },
  { id: 'technology', label: 'Technology' },
  { id: 'supply-chain', label: 'Supply Chain' },
  { id: 'competition', label: 'Competition' },
  { id: 'outlook', label: 'Outlook' },
];

export function IndustryWorkspace() {
  const { slug = '' } = useParams();
  const industry = useResource(() => intelligenceApi.industry(slug), [slug]);
  const [section, setSection] = useState<IndustrySectionKey>('overview');
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  async function researchCompany(symbol: string) {
    setBusy(symbol);
    setError('');
    try {
      const run = await researchApi.runResearch(symbol, slug);
      navigate(`/runs/${run.run_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Company analysis could not start');
    } finally {
      setBusy('');
    }
  }

  return (
    <>
      <Link to="/industries">← All industries</Link>
      <PageTitle title={industry.data?.name || 'Industry workspace'} />
      {industry.loading ? (
        <Loading />
      ) : industry.error ? (
        <ErrorBox message={industry.error} retry={industry.reload} />
      ) : industry.data ? (
        <>
          <p className="muted">
            Research questions and supporting sources are organized separately from company analysis. Only AI
            Computing Overview currently supports source-backed AI generation.
          </p>
          <div
            className="actions"
            role="tablist"
            aria-label="Industry research sections"
            style={{ marginBottom: 16 }}
          >
            {sections.map((item) => (
              <button
                type="button"
                role="tab"
                key={item.id}
                aria-selected={section === item.id}
                className={`button ${section === item.id ? '' : 'secondary'}`}
                onClick={() => setSection(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <IndustrySection key={`${slug}-${section}`} slug={slug} section={section} />
          {slug === 'ai-computing' && section === 'overview' && (
            <section className="panel">
              <h2>Original SEC evidence and cached news</h2>
              <IndustryEvidence />
              <FilingExcerpts />
            </section>
          )}
          <section className="panel">
            <h2>Guided research questions</h2>
            <p>{industry.data.prompt}</p>
            <Gaps gaps={industry.data.gaps} />
            {error && <ErrorBox message={error} />}
            {!!industry.data.symbols.length && (
              <>
                <h3>Representative company research</h3>
                <p className="muted">A company run is not a complete industry report.</p>
                <div className="actions">
                  {industry.data.symbols.map((symbol) => (
                    <button
                      type="button"
                      className="button secondary"
                      key={symbol}
                      disabled={!!busy}
                      onClick={() => void researchCompany(symbol)}
                    >
                      {busy === symbol ? 'Starting…' : `Research ${symbol} ↗`}
                    </button>
                  ))}
                </div>
              </>
            )}
          </section>
        </>
      ) : null}
    </>
  );
}
