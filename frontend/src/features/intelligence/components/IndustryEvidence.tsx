import { useState } from 'react';
import { fetchIndustryEvidence } from '../api';

type Company = { symbol: string; name: string; cik: string };
type MetricRow = {
  symbol: string;
  company: string;
  value: number;
  unit: string;
  start: string;
  end: string;
  accession: string | null;
};
type Metric = {
  key: string;
  label: string;
  concept: string;
  period: string;
  source_name: string;
  source_url: string;
  fetched_at: string;
  cached: boolean;
  rows: MetricRow[];
};
type Filing = {
  symbol: string;
  form: string;
  filed: string;
  source_name: string;
  source_url: string;
};
type Story = {
  category: string;
  headline: string;
  source_name: string;
  source_url: string;
  published_at: string;
};
type EvidenceSnapshot = {
  industry: string;
  year: number;
  mode: 'fixtures' | 'live';
  as_of: string;
  companies: Company[];
  metrics: Metric[];
  filings: Filing[];
  news: Story[];
  gaps: string[];
  coverage: string;
};

function usd(value: number) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 2,
  }).format(value / 1_000_000_000);
}

export function IndustryEvidence() {
  const [year, setYear] = useState(new Date().getUTCFullYear() - 1);
  const [data, setData] = useState<EvidenceSnapshot | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  async function load() {
    setPending(true);
    setError('');
    try {
      const next = await fetchIndustryEvidence<EvidenceSnapshot>(year);
      setData(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'SEC evidence could not be loaded.');
    } finally {
      setPending(false);
    }
  }

  return (
    <section style={{ marginTop: '1rem' }} aria-label="AI computing evidence pilot">
      <p className="eyebrow">EVIDENCE PILOT · AI COMPUTING</p>
      <p className="muted">
        A bounded research preview: SEC financial comparisons, recent filings, and previously cached industry
        headlines. No AI is invoked. This is not an industry-wide report.
      </p>
      <div className="actions">
        <label htmlFor="industry-evidence-year">Calendar-year frame</label>
        <input
          id="industry-evidence-year"
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
        <button type="button" className="button secondary" disabled={pending} onClick={() => void load()}>
          {pending ? 'Loading SEC evidence…' : 'Load SEC evidence'}
        </button>
      </div>
      {error && <p role="alert">{error}</p>}
      {data && (
        <div>
          <p className="muted">
            {data.coverage} · {data.mode === 'fixtures' ? 'Fixture mode' : 'Live official sources'} ·{' '}
            {data.as_of.slice(0, 10)}
          </p>
          <h3>Selected peers</h3>
          <p>
            {data.companies.length
              ? data.companies.map((c) => `${c.symbol} (${c.name})`).join(' · ')
              : 'No verified SEC peer mapping'}
          </p>
          <h3>Cross-company SEC metrics</h3>
          <p className="muted">
            Values in USD billions. An absent peer is not a zero. These calendar frames may reflect differing
            fiscal years.
          </p>
          {data.metrics.map((metric) => (
            <div key={metric.key}>
              <p>
                <strong>{metric.label}</strong> · {metric.period} ·{' '}
                <a href={metric.source_url} target="_blank" rel="noreferrer">
                  Original SEC frame
                </a>
              </p>
              <div style={{ overflowX: 'auto' }}>
                <table>
                  <thead>
                    <tr>
                      <th>Symbol</th>
                      <th>Reported value (USD bn)</th>
                      <th>Reporting period</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metric.rows.map((row) => (
                      <tr key={`${metric.key}-${row.symbol}`}>
                        <td>{row.symbol}</td>
                        <td>{usd(row.value)}</td>
                        <td>
                          {row.start} – {row.end}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {!metric.rows.length && (
                <p className="muted">No comparable entries returned for the selected peers.</p>
              )}
            </div>
          ))}
          {!data.metrics.length && <p className="muted">No verified SEC metric results available.</p>}
          <h3>Recent SEC filings</h3>
          <ul>
            {data.filings.map((filing) => (
              <li key={filing.source_url}>
                {filing.filed} · {filing.symbol} · {filing.form} ·{' '}
                <a href={filing.source_url} target="_blank" rel="noreferrer">
                  Open original filing
                </a>
              </li>
            ))}
          </ul>
          {!data.filings.length && <p className="muted">No filing metadata available.</p>}
          <h3>Related cached news</h3>
          <ul>
            {data.news.map((story) => (
              <li key={story.source_url}>
                {story.published_at.slice(0, 10)} · {story.source_name} ·{' '}
                <a href={story.source_url} target="_blank" rel="noreferrer">
                  {story.headline}
                </a>
              </li>
            ))}
          </ul>
          {!data.news.length && (
            <p className="muted">No cached headlines; refresh Industry Intelligence news.</p>
          )}
          <h3>Coverage limitations</h3>
          <ul>
            {data.gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
