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
  const [selected, setSelected] = useState<{ slug: string; section: IndustrySectionKey } | null>(null);
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const navigate = useNavigate();

  const defaultSection: IndustrySectionKey = industry.data?.ai_sections[0] ?? 'overview';
  const section: IndustrySectionKey = selected?.slug === slug ? selected.section : defaultSection;

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
          <p className="muted">{industry.data.research_coverage}</p>
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
                onClick={() => setSelected({ slug, section: item.id })}
              >
                {item.label}
                {industry.data?.ai_sections.includes(item.id) ? ' · AI' : ''}
              </button>
            ))}
          </div>
          <IndustrySection
            key={`${slug}-${section}`}
            slug={slug}
            section={section}
            enabledSections={industry.data.ai_sections}
          />
          {slug === 'ai-computing' && section === 'overview' ? (
            <section className="panel">
              <h2>Original SEC evidence and cached news</h2>
              <IndustryEvidence />
              <FilingExcerpts key={slug} slug={slug} />
            </section>
          ) : industry.data.research_status === 'limited_pilot' ? (
            <section className="panel">
              <h2>Original SEC 10-K filing excerpts</h2>
              <FilingExcerpts key={slug} slug={slug} />
            </section>
          ) : null}
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
