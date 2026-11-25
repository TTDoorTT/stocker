import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { EvidenceTable } from '../../../shared/ui/EvidenceTable';
import { Empty, ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, StatusBadge } from '../../../shared/ui/Presentation';
import { dateTime } from '../../../shared/utils/format';
import { researchApi } from '../api';
import type { ResearchStrategy, Run, RunEvent } from '../types';
import { AgentProgress } from './AgentProgress';
import { ResearchReportView } from './ResearchReportView';

const DEFAULT_ESTIMATES: Record<ResearchStrategy, string> = {
  multi: '~8–12 min',
  single: '~1–3 min',
};

function formatDuration(seconds: number): string {
  const total = Math.max(1, Math.round(seconds));
  if (total < 60) return `${total}s`;
  const mins = Math.floor(total / 60);
  const secs = total % 60;
  return secs ? `${mins}m ${secs}s` : `${mins}m`;
}

function estimateLabel(runs: Run[], target: ResearchStrategy): { label: string; fromHistory: boolean } {
  const matching = runs
    .filter(
      (item) =>
        item.mode === 'live' &&
        (item.strategy ?? 'multi') === target &&
        ['complete', 'incomplete'].includes(item.status) &&
        typeof item.latency_seconds === 'number' &&
        item.latency_seconds > 1,
    )
    .slice(0, 5);
  if (!matching.length) {
    return { label: DEFAULT_ESTIMATES[target], fromHistory: false };
  }
  const avg = matching.reduce((sum, item) => sum + (item.latency_seconds ?? 0), 0) / matching.length;
  if (avg < 60) {
    return { label: `~${Math.max(1, Math.round(avg))}s`, fromHistory: true };
  }
  return { label: `~${Math.max(1, Math.round(avg / 60))} min`, fromHistory: true };
}

export function DeepResearchPanel({ symbol }: { symbol: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [recentRuns, setRecentRuns] = useState<Run[]>([]);
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [strategy, setStrategy] = useState<ResearchStrategy>('multi');
  const [loadingLatest, setLoadingLatest] = useState(true);
  const [starting, setStarting] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setLoadingLatest(true);
    setError('');
    setRun(null);
    setEvents([]);
    researchApi
      .runs()
      .then((list) => {
        if (!active) return;
        setRecentRuns(list);
        const latest = list.find((item) => item.symbol.toUpperCase() === symbol.toUpperCase()) ?? null;
        setRun(latest);
      })
      .catch(() => {
        if (active) {
          setRecentRuns([]);
          setRun(null);
        }
      })
      .finally(() => {
        if (active) setLoadingLatest(false);
      });
    return () => {
      active = false;
    };
  }, [symbol]);

  const activeRunId = run?.run_id;
  const isRunning = Boolean(run && ['queued', 'running'].includes(run.status));

  useEffect(() => {
    if (!activeRunId) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      if (!activeRunId) return;
      try {
        const [value, log] = await Promise.all([
          researchApi.run(activeRunId),
          researchApi.events(activeRunId),
        ]);
        if (!active) return;
        setRun(value);
        setEvents(log);
        setError('');
        if (['queued', 'running'].includes(value.status)) {
          timer = setTimeout(poll, 1500);
        }
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : 'Research run could not be loaded');
      }
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [activeRunId]);

  async function startRun() {
    setStarting(true);
    setError('');
    try {
      const created = await researchApi.runResearch(symbol, undefined, strategy);
      setRun(created);
      setEvents([]);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Research unavailable');
    } finally {
      setStarting(false);
    }
  }

  async function stopRun() {
    if (!run) return;
    setStopping(true);
    setError('');
    try {
      const updated = await researchApi.cancelRun(run.run_id);
      setRun(updated);
      try {
        setEvents(await researchApi.events(run.run_id));
      } catch {
        // Polling will pick up the final trace if events fetch fails transiently.
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not stop research run');
    } finally {
      setStopping(false);
    }
  }

  function download() {
    if (!run?.report) return;
    const url = URL.createObjectURL(new Blob([run.report], { type: 'text/markdown;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${run.symbol}-research-${run.run_id}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const isQuickSelected = strategy === 'single';
  const runLabel = isQuickSelected ? 'Run Quick Research' : 'Run Deep Research';
  const deepEstimate = estimateLabel(recentRuns, 'multi');
  const quickEstimate = estimateLabel(recentRuns, 'single');
  const selectedEstimate = isQuickSelected ? quickEstimate : deepEstimate;
  const activeRunEstimate = estimateLabel(recentRuns, run?.strategy ?? strategy);

  return (
    <section className="panel" aria-label="Research workspace">
      <div className="panel-heading">
        <div>
          <h2>Research · {symbol}</h2>
          <small>
            {isQuickSelected
              ? `Quick Research: fast 1-pass executive brief from captured filings, quote, and core metrics · Est. ${quickEstimate.label}`
              : `Deep Research: full 6-stage analysis (profile → financials → expectations → valuation → risk → report) · Est. ${deepEstimate.label}`}
            {selectedEstimate.fromHistory ? ' (based on recent runs)' : ''}
          </small>
        </div>
        <div className="actions">
          <select
            aria-label="Research mode"
            className="research-depth-select"
            value={strategy}
            disabled={isRunning || starting}
            onChange={(event) => setStrategy(event.target.value as ResearchStrategy)}
          >
            <option value="multi">Deep Research (6-stage · {deepEstimate.label})</option>
            <option value="single">Quick Research (1-pass · {quickEstimate.label})</option>
          </select>
          {isRunning ? (
            <button
              type="button"
              className="button danger"
              onClick={() => void stopRun()}
              disabled={stopping}
            >
              {stopping ? 'Stopping…' : 'Stop Research'}
            </button>
          ) : (
            <button type="button" className="button" onClick={() => void startRun()} disabled={starting}>
              {starting ? 'Starting…' : runLabel}
            </button>
          )}
        </div>
      </div>

      {error && <ErrorBox message={error} />}

      {loadingLatest ? (
        <Loading />
      ) : !run ? (
        <Empty>
          No research run yet for {symbol}. Pick <strong>Deep Research</strong> ({deepEstimate.label}) or{' '}
          <strong>Quick Research</strong> ({quickEstimate.label}) and click <strong>{runLabel}</strong>.
        </Empty>
      ) : (
        <>
          <div className="run-meta">
            <span className="badge">{run.strategy === 'single' ? 'Quick Research' : 'Deep Research'}</span>
            <ModeBadge mode={run.mode} />
            <StatusBadge status={run.status} />
            <span>Started {dateTime(run.started_at)}</span>
            {typeof run.latency_seconds === 'number' && run.latency_seconds > 0 && (
              <span>Duration {formatDuration(run.latency_seconds)}</span>
            )}
            <span>Model: {run.model_id}</span>
            <Link to={`/runs/${run.run_id}`}>Open full record ↗</Link>
          </div>
          <AgentProgress run={run} />
          {isRunning && (
            <p role="status" className="notice">
              <span className="spinner" /> Agents are executing (Est. {activeRunEstimate.label}). Click{' '}
              <strong>Stop Research</strong> to interrupt this run.
            </p>
          )}
          {run.status === 'cancelled' && (
            <p role="status" className="notice">
              This research run was stopped before completion. Click <strong>{runLabel}</strong> to start a
              new run.
            </p>
          )}
          {!run.report && <Gaps gaps={run.gaps} />}
          {run.error && <ErrorBox message={run.error} />}
          <div className="panel report" style={{ marginTop: 18 }}>
            <div className="panel-heading">
              <h3>Research report</h3>
              {run.report && (
                <button type="button" className="button secondary" onClick={download}>
                  Download Markdown ↓
                </button>
              )}
            </div>
            {run.report ? (
              <ResearchReportView markdown={run.report} />
            ) : (
              <Empty>
                {isRunning
                  ? 'The final report appears after validated stage handoffs.'
                  : 'A report is unavailable for this run. Review the stage trace below.'}
              </Empty>
            )}
          </div>
          {run.report && Boolean(run.gaps?.length) && (
            <details className="stage-detail" style={{ marginTop: 14 }}>
              <summary>
                <strong>All recorded stage data limitations</strong> · {run.gaps.length} entries
              </summary>
              <Gaps gaps={run.gaps} />
            </details>
          )}
          <details className="stage-detail" style={{ marginTop: 14 }}>
            <summary>
              <strong>Agent handoffs &amp; validation</strong> · {run.stages?.length || 0} recorded attempts
            </summary>
            {run.stages?.length ? (
              run.stages.map((stage, i) => (
                <details key={`${stage.stage}-${stage.attempt}-${i}`} className="stage-detail">
                  <summary>
                    <strong>{stage.stage}</strong> · attempt {stage.attempt}{' '}
                    <StatusBadge status={stage.status} />
                  </summary>
                  {stage.output?.summary && <p>{stage.output.summary}</p>}
                  {stage.validation_errors?.length > 0 && (
                    <div className="notice error">
                      <strong>Validation errors</strong>
                      <ul>
                        {stage.validation_errors.map((value, j) => (
                          <li key={j}>{value}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                  <pre>{JSON.stringify(stage.output, null, 2)}</pre>
                </details>
              ))
            ) : (
              <Empty>No stage attempt recorded yet.</Empty>
            )}
          </details>
          <details className="stage-detail">
            <summary>
              <strong>Execution trace</strong> · {events.length} events
            </summary>
            {events.length ? (
              <div className="bounded-panel-body">
                <ol className="event-log">
                  {events.map((event) => (
                    <li key={event.id}>
                      <span className="event-dot" />
                      <div>
                        <strong>{event.event.replaceAll('_', ' ')}</strong>
                        {event.stage && <span className="badge">{event.stage}</span>}
                        <small>{dateTime(event.at || event.timestamp)}</small>
                      </div>
                    </li>
                  ))}
                </ol>
              </div>
            ) : (
              <Empty>No events recorded yet.</Empty>
            )}
          </details>
          <details className="stage-detail">
            <summary>
              <strong>Captured evidence</strong> · {run.evidence?.length || 0} records
            </summary>
            <div className="bounded-panel-body">
              <EvidenceTable evidence={run.evidence || []} />
            </div>
          </details>
        </>
      )}
    </section>
  );
}
