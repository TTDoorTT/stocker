import { useState } from 'react';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, SourceLink } from '../../../shared/ui/Presentation';
import { marketApi } from '../api';
import { chartGeometry, formatFinancial, quarterSeries } from '../quarterlyMath';
import type { FinancialMetricName, FinancialTrendsResponse } from '../types';

const METRICS: { key: FinancialMetricName; label: string }[] = [
  { key: 'revenue', label: 'Revenue' },
  { key: 'net_income', label: 'Net income' },
  { key: 'gross_profit', label: 'Gross profit' },
  { key: 'operating_cash_flow', label: 'Operating cash flow' },
  { key: 'diluted_eps', label: 'Diluted EPS' },
];

function QuarterlyBars({
  response,
  metric,
}: {
  response: FinancialTrendsResponse;
  metric: FinancialMetricName;
}) {
  const observations = quarterSeries(response.periods, metric);
  const geometry = chartGeometry(observations.map((row) => row.value));
  if (!observations.length || !geometry) {
    return <Empty>No comparable quarterly observations are available for this metric.</Empty>;
  }
  const plotLeft = 45;
  const plotRight = 800;
  const width = (plotRight - plotLeft) / observations.length;
  const barWidth = Math.min(44, width * 0.58);
  return (
    <div className="quarterly-plot" role="group" aria-label="Quarterly financial visualization">
      <svg
        viewBox="0 0 840 245"
        role="img"
        aria-label={`Quarterly ${METRICS.find((item) => item.key === metric)?.label} chart`}
      >
        <title>Quarterly sourced financial observations; refer to the table for exact values</title>
        <line
          x1={plotLeft}
          x2={plotRight}
          y1={geometry.baseline}
          y2={geometry.baseline}
          stroke="var(--border)"
        />
        {observations.map((row, index) => {
          const x = plotLeft + width * index + (width - barWidth) / 2;
          const y = row.value === null ? geometry.baseline : geometry.y(row.value);
          const top = Math.min(y, geometry.baseline);
          const height = Math.max(1.5, Math.abs(y - geometry.baseline));
          return (
            <g key={row.id}>
              {row.value === null ? (
                <rect
                  x={x}
                  y={geometry.baseline - 1}
                  width={barWidth}
                  height={2}
                  fill="var(--muted)"
                  opacity="0.55"
                />
              ) : (
                <rect
                  x={x}
                  y={top}
                  width={barWidth}
                  height={height}
                  rx={3}
                  fill={row.value < 0 ? 'var(--negative)' : 'var(--accent)'}
                  opacity={row.status === 'derived' ? '0.67' : '0.9'}
                />
              )}
              <text
                x={plotLeft + width * (index + 0.5)}
                y={225}
                textAnchor="middle"
                fontSize="12"
                fill="var(--muted)"
              >
                {row.label.replace(' FY', ' ')}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="muted quarterly-explainer">
        Bars show sourced or derived standalone quarters. Faded bars are derived; dashes indicate missing
        values. The zero line is retained for negative results.
      </p>
    </div>
  );
}

export function QuarterlyTrendsPanel({ symbol }: { symbol: string }) {
  const [metric, setMetric] = useState<FinancialMetricName>('revenue');
  const request = useResource(() => marketApi.financialTrends(symbol), [symbol]);
  return (
    <section className="panel quarterly-panel" aria-label="Quarterly financial trends">
      <div className="panel-heading">
        <h2>Quarterly financial trends</h2>
        {request.data && <ModeBadge mode={request.data.mode} />}
      </div>
      {request.loading ? (
        <Loading />
      ) : request.error ? (
        <ErrorBox message={request.error} retry={request.reload} />
      ) : !request.data ? (
        <Empty>Quarterly financials unavailable.</Empty>
      ) : (
        <FinancialTrendsContent response={request.data} metric={metric} setMetric={setMetric} />
      )}
    </section>
  );
}

function FinancialTrendsContent({
  response,
  metric,
  setMetric,
}: {
  response: FinancialTrendsResponse;
  metric: FinancialMetricName;
  setMetric: (metric: FinancialMetricName) => void;
}) {
  const active = METRICS.find((item) => item.key === metric)!;
  const rows = quarterSeries(response.periods, metric);
  const ttm = response.ttm[metric];
  return (
    <>
      <div className="quarterly-metrics" role="group" aria-label="Financial metric">
        {METRICS.map((item) => (
          <button
            key={item.key}
            type="button"
            className={`quarterly-metric-button${metric === item.key ? ' selected' : ''}`}
            aria-pressed={metric === item.key}
            onClick={() => setMetric(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="quarterly-summary">
        <div>
          <span className="muted">{active.label} · recent quarters</span>
          <strong>{rows.filter((row) => row.value !== null).length} observations</strong>
        </div>
        <div>
          <span className="muted">Trailing 12 months</span>
          <strong>
            {ttm?.status === 'available' && ttm.value !== null
              ? formatFinancial(ttm.value, metric, response.currency)
              : 'Unavailable'}
          </strong>
          {ttm?.status === 'unavailable' && <small>{ttm.reason}</small>}
        </div>
      </div>
      <QuarterlyBars response={response} metric={metric} />
      <div className="table-scroll quarterly-table">
        <table>
          <caption className="sr-only">
            Quarterly {active.label} with fiscal dates, filing status and original evidence
          </caption>
          <thead>
            <tr>
              <th>Fiscal quarter</th>
              <th>Period end</th>
              <th>Amount</th>
              <th>Basis</th>
              <th>Filed</th>
            </tr>
          </thead>
          <tbody>
            {[...response.periods]
              .filter((period) => period.period_kind === 'standalone_quarter')
              .sort((a, b) => b.period_end.localeCompare(a.period_end))
              .slice(0, 8)
              .map((period) => {
                const observation = period.metrics[metric];
                return (
                  <tr key={period.period_id}>
                    <td>
                      {period.fiscal_quarter} FY{period.fiscal_year}
                    </td>
                    <td>{period.period_end}</td>
                    <td>{formatFinancial(observation?.value ?? null, metric, response.currency)}</td>
                    <td>
                      {observation?.status === 'derived'
                        ? 'Calculated from filings'
                        : observation?.status === 'as_reported'
                          ? 'Reported'
                          : 'Unavailable'}
                    </td>
                    <td>{period.filed_on}</td>
                  </tr>
                );
              })}
          </tbody>
        </table>
      </div>
      {response.sources.length > 0 && (
        <p className="quarterly-source">
          Source:{' '}
          {response.sources.map((source, i) => (
            <span key={`${source.url}:${i}`}>
              {i > 0 ? ', ' : ''}
              <SourceLink url={source.url} name={source.name} />
              {source.cached ? ' · cached' : ''}
              {source.fixture ? ' · SYNTHETIC' : ''}
            </span>
          ))}
        </p>
      )}
      {response.gaps.length > 0 && (
        <details className="quarterly-gaps">
          <summary>Data coverage and calculation limitations ({response.gaps.length})</summary>
          <ul>
            {response.gaps.map((gap) => (
              <li key={gap}>{gap}</li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}
