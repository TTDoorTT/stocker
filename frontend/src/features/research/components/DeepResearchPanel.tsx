import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Link } from 'react-router-dom';
import { EvidenceTable } from '../../../shared/ui/EvidenceTable';
import { Empty, ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, StatusBadge } from '../../../shared/ui/Presentation';
import { dateTime } from '../../../shared/utils/format';
import { researchApi } from '../api';
import type { Run, RunEvent } from '../types';
import { AgentProgress } from './AgentProgress';

export function DeepResearchPanel({ symbol }: { symbol: string }) {
  const [run, setRun] = useState<Run | null>(null);
  const [events, setEvents] = useState<RunEvent[]>([]);
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
        const latest = list.find((item) => item.symbol.toUpperCase() === symbol.toUpperCase()) ?? null;
        setRun(latest);
      })
      .catch(() => {
        if (active) setRun(null);
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
      const created = await researchApi.runResearch(symbol);
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

  return (
    <section className="panel" aria-label="Deep research workspace">
      <div className="panel-heading">
        <div>
          <h2>Deep Research · {symbol}</h2>
          <small>
            Six-stage evidence-bound analysis: profile → financials → expectations → valuation → risk → report
          </small>
        </div>
        <div className="actions">
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
              {starting ? 'Starting…' : 'Run Deep Research'}
            </button>
          )}
        </div>
      </div>

      {error && <ErrorBox message={error} />}

      {loadingLatest ? (
        <Loading />
      ) : !run ? (
        <Empty>
          No deep research run yet for {symbol}. Click <strong>Run Deep Research</strong> to launch a
          six-stage evidence-backed analysis.
        </Empty>
      ) : (
        <>
          <div className="run-meta">
            <ModeBadge mode={run.mode} />
            <StatusBadge status={run.status} />
            <span>Started {dateTime(run.started_at)}</span>
            <span>Model: {run.model_id}</span>
            <Link to={`/runs/${run.run_id}`}>Open full record ↗</Link>
          </div>
          <AgentProgress run={run} />
          {isRunning && (
            <p role="status" className="notice">
              <span className="spinner" /> Agents are executing. Click <strong>Stop Research</strong> to
              interrupt this run.
            </p>
          )}
          {run.status === 'cancelled' && (
            <p role="status" className="notice">
              This research run was stopped before completion. Click <strong>Run Deep Research</strong> to
              start a new run.
            </p>
          )}
          <Gaps gaps={run.gaps} />
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
              <div className="markdown">
                <ReactMarkdown>{run.report}</ReactMarkdown>
              </div>
            ) : (
              <Empty>
                {isRunning
                  ? 'The final report appears after validated stage handoffs.'
                  : 'A report is unavailable for this run. Review the stage trace below.'}
              </Empty>
            )}
          </div>
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
