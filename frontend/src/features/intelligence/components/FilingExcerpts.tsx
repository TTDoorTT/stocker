import { useState } from 'react';
import { ErrorBox, Gaps } from '../../../shared/ui/Feedback';
import { intelligenceApi } from '../api';
import type { FilingExcerptsResponse } from '../types';

export function FilingExcerpts() {
  const [year, setYear] = useState(new Date().getUTCFullYear() - 1);
  const [data, setData] = useState<FilingExcerptsResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  async function load() {
    setBusy(true);
    setError('');
    try {
      setData(await intelligenceApi.filingExcerpts(year));
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Filing excerpts unavailable');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-label="SEC filing text excerpts" style={{ marginTop: '1.5rem' }}>
      <h3>SEC 10-K filing excerpts</h3>
      <p className="muted">
        Short, literal passages from selected SEC filings. These are keyword matches, not verified research
        findings. This button does not invoke an AI model.
      </p>
      <div className="actions">
        <label htmlFor="sec-excerpts-year">Financial frame year</label>
        <input
          id="sec-excerpts-year"
          type="number"
          min={2009}
          max={new Date().getUTCFullYear() - 1}
          value={year}
          onChange={(event) => {
            setYear(Number(event.target.value));
            setData(null);
          }}
          style={{ width: '7rem' }}
        />
        <button type="button" className="button secondary" onClick={() => void load()} disabled={busy}>
          {busy ? 'Loading SEC text…' : 'Load SEC filing excerpts'}
        </button>
      </div>
      {error && <ErrorBox message={error} />}
      {data && (
        <div>
          <p className="muted">{data.coverage}</p>
          {data.excerpts.map((excerpt, index) => (
            <div
              key={`${excerpt.source_url}-${index}`}
              style={{ borderBottom: '1px solid var(--border)', padding: '0.8rem 0' }}
            >
              <p>
                <strong>{excerpt.symbol}</strong> · {excerpt.form} · Filed {excerpt.filed} · Match:{' '}
                <em>{excerpt.matched_term}</em>
              </p>
              <blockquote
                style={{ margin: '0.5rem 0', paddingLeft: '0.8rem', borderLeft: '2px solid var(--border)' }}
              >
                {excerpt.text}
              </blockquote>
              <a href={excerpt.source_url} target="_blank" rel="noopener noreferrer">
                Original SEC filing
              </a>
              {excerpt.cached && <small>Cached source response</small>}
            </div>
          ))}
          {!data.excerpts.length && <p className="muted">No usable text excerpts retrieved.</p>}
          <Gaps gaps={data.gaps} />
        </div>
      )}
    </section>
  );
}
