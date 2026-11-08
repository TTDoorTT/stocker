import { useEffect, useRef, useState } from 'react';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, SourceLink } from '../../../shared/ui/Presentation';
import { marketApi } from '../api';
import type { DriftPoint } from '../eventStudyMath';
import { driftBounds, eventPath, formatDrift, formatPositiveShare, meanPath } from '../eventStudyMath';
import type { EventStudyResponse, EventsResponse } from '../types';

const HORIZONS = ['1', '5', '20'] as const;
const TICKS = [-5, 0, 5, 10, 15, 20];

function DriftChart({ study }: { study: EventStudyResponse }) {
  const [selection, setSelection] = useState('mean');
  const aggregate = meanPath(study);
  const eligible = study.events.filter((event) => event.eligible && eventPath(event).length === 26);
  const selected = eligible.find((event) => event.event_id === selection);
  const points: DriftPoint[] = selected
    ? eventPath(selected)
    : aggregate.length
      ? aggregate
      : eligible.length
        ? eventPath(eligible[0])
        : [];
  const bounds = driftBounds(points);

  if (!bounds) {
    return <Empty>No complete eligible return path is available to chart.</Empty>;
  }

  const left = 66;
  const right = 820;
  const top = 22;
  const bottom = 230;
  const x = (day: number) => left + ((day + 5) / 25) * (right - left);
  const y = (value: number) =>
    bottom - ((value - bounds.minimum) / (bounds.maximum - bounds.minimum)) * (bottom - top);
  const path = points
    .map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(point.day)} ${y(point.value)}`)
    .join(' ');
  const meanSelected = !selected && aggregate.length > 0;

  return (
    <div className="event-study-chart">
      <div className="event-study-chart-toolbar">
        <div>
          <strong>{meanSelected ? 'Mean eligible-event drift' : 'Individual historical event'}</strong>
          <small>SPY-relative adjusted-close performance · percentage points</small>
        </div>
        <label>
          View
          <select
            aria-label="Event path"
            value={meanSelected ? 'mean' : (selected?.event_id ?? eligible[0].event_id)}
            onChange={(event) => setSelection(event.target.value)}
          >
            {aggregate.length > 0 && (
              <option value="mean">Mean ({study.eligible_event_count} eligible)</option>
            )}
            {eligible.map((event) => (
              <option key={event.event_id} value={event.event_id}>
                {event.event_id.split(':').at(-1)} · {event.day_zero}
              </option>
            ))}
          </select>
        </label>
      </div>
      <svg viewBox="0 0 860 270" role="img" aria-label="SPY-relative post-date drift chart">
        <title>Daily return difference versus SPY, anchored to the first post-date trading close</title>
        {[bounds.minimum, 0, bounds.maximum].map((level) => (
          <g key={level}>
            <line
              x1={left}
              x2={right}
              y1={y(level)}
              y2={y(level)}
              stroke="var(--border)"
              strokeDasharray={level === 0 ? undefined : '3 5'}
            />
            <text x={left - 8} y={y(level) + 4} textAnchor="end" fontSize="12" fill="var(--muted)">
              {level.toFixed(1)}
            </text>
          </g>
        ))}
        <line x1={x(0)} x2={x(0)} y1={top} y2={bottom} stroke="var(--muted)" strokeDasharray="4 5" />
        <path d={path} fill="none" stroke="var(--accent)" strokeWidth="2.8" strokeLinejoin="round" />
        {points
          .filter((point) => [0, 1, 5, 20].includes(point.day))
          .map((point) => (
            <circle key={point.day} cx={x(point.day)} cy={y(point.value)} r="3.5" fill="var(--accent)" />
          ))}
        {TICKS.map((day) => (
          <text key={day} x={x(day)} y="255" textAnchor="middle" fontSize="12" fill="var(--muted)">
            {day > 0 ? `+${day}` : day}
          </text>
        ))}
      </svg>
      <p className="muted event-study-caption">
        Day 0 = first trading close strictly after the vendor-reported date. The initial announcement jump is
        excluded. Negative days are relative to the same day-0 close.
      </p>
    </div>
  );
}

function SourceDetails({ data }: { data: EventsResponse | EventStudyResponse }) {
  return (
    <>
      {data.sources.length > 0 && (
        <p className="event-study-sources">
          Sources:{' '}
          {data.sources.map((source, index) => (
            <span key={`${source.url}:${index}`}>
              {index ? ' · ' : ''}
              <SourceLink url={source.url} name={source.name} />
              {source.fixture ? ' · SYNTHETIC' : ''}
              {source.cached ? ' · cached' : ''}
            </span>
          ))}
        </p>
      )}
      {data.gaps.length > 0 && (
        <details className="event-study-gaps">
          <summary>Coverage and methodology limitations ({data.gaps.length})</summary>
          <ul>
            {data.gaps.map((gap, index) => (
              <li key={`${index}:${gap}`}>{gap}</li>
            ))}
          </ul>
        </details>
      )}
    </>
  );
}

function StudyResults({ study, events }: { study: EventStudyResponse; events: EventsResponse }) {
  const lookup = new Map(events.events.map((event) => [event.event_id, event]));
  const summary = study.summary ?? [];
  return (
    <div className="event-study-results">
      <div className="event-study-stats">
        <div>
          <span className="muted">Eligible completed events</span>
          <strong>
            {study.eligible_event_count}/{study.events.length}
          </strong>
        </div>
        <div>
          <span className="muted">Benchmark</span>
          <strong>{study.benchmark_symbol}</strong>
        </div>
        <div>
          <span className="muted">Completed window</span>
          <strong>
            −{study.pre_trading_days} to +{study.post_trading_days} sessions
          </strong>
        </div>
      </div>
      {summary.length > 0 ? (
        <div className="event-study-summary" aria-label="Aggregate event statistics">
          {summary.map((item) => (
            <div key={item.horizon}>
              <span className="muted">
                Horizon {item.horizon} · {item.eligible_n} events
              </span>
              <strong
                className={item.mean_excess_return < 0 ? 'event-study-negative' : 'event-study-positive'}
              >
                {formatDrift(item.mean_excess_return)}
              </strong>
              <small>Median {formatDrift(item.median_excess_return)}</small>
              <small>Positive share {formatPositiveShare(item.positive_share)}</small>
            </div>
          ))}
        </div>
      ) : (
        <p className="event-study-insufficient" role="status">
          Aggregate statistics withheld: at least {study.minimum_sample} eligible, complete, non-overlapping
          events are required.
        </p>
      )}
      <DriftChart study={study} />
      <h3>Historical events and exclusions</h3>
      <div className="table-scroll event-study-table">
        <table>
          <caption className="sr-only">
            Vendor-dated earnings events, eligibility and SPY-relative post-date drift
          </caption>
          <thead>
            <tr>
              <th>Fiscal event</th>
              <th>Vendor date</th>
              <th>Day 0 close</th>
              <th>Status</th>
              <th>+1</th>
              <th>+5</th>
              <th>+20</th>
            </tr>
          </thead>
          <tbody>
            {study.events.map((row) => (
              <tr key={row.event_id}>
                <td>{row.event_id.split(':').at(-1)}</td>
                <td>{lookup.get(row.event_id)?.event_date ?? 'Unverified'}</td>
                <td>{row.day_zero ?? '—'}</td>
                <td>{row.eligible ? 'Eligible' : (row.exclusion_reason ?? 'Excluded')}</td>
                {HORIZONS.map((horizon) => (
                  <td key={horizon} className="event-study-number">
                    {row.eligible ? formatDrift(row.excess_returns[horizon]) : '—'}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <SourceDetails data={study} />
    </div>
  );
}

export function EventStudyPanel({ symbol }: { symbol: string }) {
  const events = useResource(() => marketApi.events(symbol), [symbol]);
  const [study, setStudy] = useState<EventStudyResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [runError, setRunError] = useState('');
  const sequence = useRef(0);
  useEffect(
    () => () => {
      sequence.current += 1;
    },
    [],
  );

  async function run() {
    const current = ++sequence.current;
    setPending(true);
    setRunError('');
    setStudy(null);
    try {
      const result = await marketApi.eventStudy(symbol);
      if (current === sequence.current) setStudy(result);
    } catch (error) {
      if (current === sequence.current)
        setRunError(error instanceof Error ? error.message : 'Event study unavailable');
    } finally {
      if (current === sequence.current) setPending(false);
    }
  }

  return (
    <section className="panel event-study-panel" aria-label="Historical event study">
      <div className="panel-heading">
        <div>
          <h2>Historical event study</h2>
          <small className="muted">Earnings dates · post-date drift versus SPY</small>
        </div>
        {events.data && <ModeBadge mode={events.data.mode} />}
      </div>
      <p className="event-study-disclosure">
        Historical comparison only. Vendor-reported earnings dates do not establish exact release times or
        causality. Running the study requests five years of adjusted daily prices for the stock and SPY; no AI
        is called.
      </p>
      {events.loading ? (
        <Loading />
      ) : events.error ? (
        <ErrorBox message={events.error} retry={events.reload} />
      ) : events.data ? (
        <>
          <div className="event-study-actions">
            <span>{events.data.events.length} dated historical event(s) available</span>
            <button
              type="button"
              className="button"
              disabled={pending || events.data.events.length === 0}
              onClick={run}
            >
              {pending ? 'Calculating…' : study ? 'Rerun event study' : 'Run event study'}
            </button>
          </div>
          {events.data.events.length === 0 && (
            <Empty>No usable earnings dates are available for an event study.</Empty>
          )}
          {pending && (
            <p role="status" className="muted">
              Calculating historical stock/SPY returns…
            </p>
          )}
          {runError && <ErrorBox message={runError} retry={run} />}
          {study && <StudyResults study={study} events={events.data} />}
          {!study && <SourceDetails data={events.data} />}
        </>
      ) : (
        <Empty>Historical event dates unavailable.</Empty>
      )}
    </section>
  );
}
