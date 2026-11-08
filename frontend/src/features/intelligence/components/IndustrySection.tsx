import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { EvidenceTable } from '../../../shared/ui/EvidenceTable';
import { ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { intelligenceApi } from '../api';
import type { IndustrySectionKey, SavedIndustrySection } from '../types';

const descriptions: Record<IndustrySectionKey, string> = {
  overview: 'Definition, demand context, key participants and sourced recent developments.',
  technology: 'Competing technology routes, technical dependencies and adoption milestones.',
  'supply-chain': 'Upstream inputs, production bottlenecks, customers and value distribution.',
  competition: 'Company roles, comparable reporting periods and competitive structure.',
  outlook: 'Measurable milestones, unresolved uncertainties and sector risks.',
};

export function IndustrySection({
  slug,
  section,
  enabledSections,
}: {
  slug: string;
  section: IndustrySectionKey;
  enabledSections: IndustrySectionKey[];
}) {
  const [saved, setSaved] = useState<SavedIndustrySection | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const enabled = enabledSections.includes(section);
  const sectionLabel: Record<IndustrySectionKey, string> = {
    overview: 'Overview',
    technology: 'Technology',
    'supply-chain': 'Supply Chain',
    competition: 'Competition',
    outlook: 'Outlook',
  };

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError('');
    setSaved(null);
    void intelligenceApi
      .savedIndustrySection(slug, section)
      .then((data) => {
        if (active) setSaved(data);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Unable to read saved research');
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [slug, section]);

  async function generate() {
    setBusy(true);
    setError('');
    try {
      const result = await intelligenceApi.generateIndustrySection(slug, section);
      setSaved(result);
    } catch (err) {
      // Keep the previous successful output on screen if regeneration fails.
      setError(err instanceof Error ? err.message : 'Research generation failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" aria-label={`${section} industry research section`}>
      <p className="eyebrow">INDUSTRY RESEARCH SECTION</p>
      <h2>{section === 'supply-chain' ? 'Supply Chain' : section[0].toUpperCase() + section.slice(1)}</h2>
      <p className="muted">{descriptions[section]}</p>
      {loading && <Loading />}
      {error && <ErrorBox message={error} />}
      {!loading && (
        <>
          {saved?.saved && saved.result ? (
            <>
              <p className="muted">
                Saved {saved.generated_at?.slice(0, 19).replace('T', ' ')} UTC · Model: {saved.model_id}
                {saved.stale ? ' · Potentially outdated — refresh the research to update evidence' : ''}
              </p>
              {saved.result.filing_coverage && (
                <p className="muted" aria-label="Filing evidence coverage">
                  Accepted excerpts: {saved.result.filing_coverage.accepted_excerpts}. Issuers represented:{' '}
                  {saved.result.filing_coverage.represented_issuers.length} of{' '}
                  {saved.result.filing_coverage.selected_issuers.length} selected.
                  {saved.result.filing_coverage.missing_issuers.length > 0 &&
                    ` Missing selected issuers: ${saved.result.filing_coverage.missing_issuers.join(', ')}.`}{' '}
                  These counts do not establish industry-wide coverage or claim support.
                </p>
              )}
              {saved.result.filing_coverage?.cited_issuers && (
                <p className="muted" aria-label="Model-screened claim citation coverage">
                  Cited issuers: {saved.result.filing_coverage.cited_issuers.length} of{' '}
                  {saved.result.filing_coverage.represented_issuers.length} represented. Distinct cited
                  excerpts: {saved.result.filing_coverage.cited_excerpts}. Model-screened claims:{' '}
                  {saved.result.filing_coverage.model_screened_claims}.
                  {!!saved.result.filing_coverage.uncited_represented_issuers?.length &&
                    ` Accepted but not cited: ${saved.result.filing_coverage.uncited_represented_issuers.join(', ')}.`}{' '}
                  Citation counts do not establish independent factual verification.
                </p>
              )}
              <div className="markdown">
                <ReactMarkdown>{saved.result.answer}</ReactMarkdown>
              </div>
              <Gaps gaps={saved.result.gaps} />
              <details>
                <summary>Captured supporting evidence ({saved.result.evidence.length})</summary>
                <EvidenceTable evidence={saved.result.evidence} />
              </details>
            </>
          ) : (
            <p className="muted">No saved research for this section.</p>
          )}
          {enabled ? (
            <div className="actions" style={{ marginTop: '1rem' }}>
              <button type="button" className="button" disabled={busy} onClick={() => void generate()}>
                {busy
                  ? 'Generating with configured AI…'
                  : saved?.saved
                    ? `Regenerate ${sectionLabel[section]}`
                    : `Generate ${sectionLabel[section]}`}
              </button>
            </div>
          ) : (
            <p className="muted">
              Guided workspace only. Automated research is not enabled until trustworthy source coverage
              exists for this industry and section.
            </p>
          )}
        </>
      )}
    </section>
  );
}
