import { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { Link, useParams } from 'react-router-dom';
import { EvidenceTable } from '../../../shared/ui/EvidenceTable';
import { Empty, ErrorBox, Gaps, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, PageTitle, StatusBadge } from '../../../shared/ui/Presentation';
import { dateTime } from '../../../shared/utils/format';
import { researchApi } from '../api';
import { AgentProgress } from '../components/AgentProgress';
import type { Run, RunEvent } from '../types';

export function ResearchRun() {
  const { id = '' } = useParams();
  const [run, setRun] = useState<Run>();
  const [events, setEvents] = useState<RunEvent[]>([]);
  const [error, setError] = useState('');
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    let active = true;
    let timer: ReturnType<typeof setTimeout>;
    setRun(undefined);
    setError('');
    async function poll() {
      try {
        const [value, log] = await Promise.all([researchApi.run(id), researchApi.events(id)]);
        if (!active) return;
        setRun(value);
        setEvents(log);
        setError('');
        if (['queued', 'running'].includes(value.status)) timer = setTimeout(poll, 1500);
      } catch (e) {
        if (active) setError(e instanceof Error ? e.message : 'Run could not be loaded');
      }
    }
    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [id, retry]);
  if (!run) return error ? <ErrorBox message={error} retry={() => setRetry((v) => v + 1)} /> : <Loading />;
  const isRunning = ['queued', 'running'].includes(run.status);
  function download() {
    const url = URL.createObjectURL(new Blob([run?.report || ''], { type: 'text/markdown;charset=utf-8' }));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `${run?.symbol}-research-${id}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  }
  return (
    <>
      <PageTitle eyebrow="RESEARCH / EXECUTION RECORD" title={`${run.symbol} research`}>
        <div className="actions">
          <ModeBadge mode={run.mode} />
          <StatusBadge status={run.status} />
        </div>
      </PageTitle>
      <div className="run-meta">
        <span>Started {dateTime(run.started_at)}</span>
        <span>Model: {run.model_id}</span>
        <code>{run.run_id}</code>
      </div>
      {error && <ErrorBox message={error} retry={() => setRetry((v) => v + 1)} />}
      <AgentProgress run={run} />
      {isRunning && (
        <p role="status" className="notice">
          <span className="spinner" /> Agents are executing. This page polls stored run state; stages update
          when the backend records real events.
        </p>
      )}
      <Gaps gaps={run.gaps} />
      {run.error && <ErrorBox message={run.error} />}
      <section className="panel report">
        <div className="panel-heading">
          <h2>Research report</h2>
          {run.report && (
            <button className="button secondary" onClick={download}>
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
              : 'A report is unavailable for this run. Review the trace and validation errors below.'}
          </Empty>
        )}
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h2>Agent handoffs & validation</h2>
          <span>{run.stages?.length || 0} recorded attempts</span>
        </div>
        {run.stages?.length ? (
          run.stages.map((stage, i) => (
            <details key={`${stage.stage}-${stage.attempt}-${i}`} className="stage-detail">
              <summary>
                <strong>{stage.stage}</strong> · attempt {stage.attempt} <StatusBadge status={stage.status} />
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
              <h3>Stage input references</h3>
              <p>
                <code>{stage.input_evidence_ids?.join(', ') || 'No input references recorded'}</code>
              </p>
              <details>
                <summary>Scoped stage input</summary>
                <pre>{JSON.stringify(stage.input, null, 2)}</pre>
              </details>
              <h3>Structured output</h3>
              <pre>{JSON.stringify(stage.output, null, 2)}</pre>
            </details>
          ))
        ) : (
          <Empty>No stage attempt recorded yet.</Empty>
        )}
      </section>
      <section className="panel">
        <h2>Execution trace</h2>
        {events.length ? (
          <ol className="event-log">
            {events.map((event) => (
              <li key={event.id}>
                <span className="event-dot" />
                <div>
                  <strong>{event.event.replaceAll('_', ' ')}</strong>
                  {event.stage && <span className="badge">{event.stage}</span>}
                  <small>{dateTime(event.at || event.timestamp)}</small>
                  <details>
                    <summary>Event details</summary>
                    <pre>{JSON.stringify(event, null, 2)}</pre>
                  </details>
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <Empty>No events recorded yet.</Empty>
        )}
      </section>
      <section className="panel">
        <h2>Captured evidence</h2>
        <EvidenceTable evidence={run.evidence || []} />
      </section>
      <section className="panel">
        <h2>Deterministic calculation log</h2>
        {run.calculations?.length ? (
          <div className="calculation-grid">
            {run.calculations.map((calc, i) => (
              <details key={calc.calculation_id || calc.id || i}>
                <summary>
                  <code>{calc.calculation_id || calc.id}</code> · {calc.metric || 'Calculation'}
                </summary>
                <pre>{JSON.stringify(calc, null, 2)}</pre>
              </details>
            ))}
          </div>
        ) : (
          <Empty>No calculations available.</Empty>
        )}
      </section>
      <Link to="/records">← Research records</Link>
    </>
  );
}
