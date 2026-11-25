import { StatusBadge } from '../../../shared/ui/Presentation';
import type { Run } from '../types';

const deepStages = ['profile', 'financials', 'estimates', 'valuation', 'risk', 'report'];

export function AgentProgress({ run }: { run: Run }) {
  if (run.strategy === 'single') {
    const reportStage = run.stages?.filter((s) => s.stage === 'report').at(-1);
    const dataCaptured =
      Boolean(run.evidence?.length || run.calculations?.length) ||
      Boolean(reportStage) ||
      ['complete', 'incomplete'].includes(run.status);
    const captureStatus = dataCaptured
      ? 'complete'
      : run.status === 'failed'
        ? 'failed'
        : run.status === 'cancelled'
          ? 'cancelled'
          : run.status === 'running'
            ? 'running'
            : 'pending';
    return (
      <div className="stage-grid quick" aria-label="Quick research stage progress">
        <div className={`stage-card ${captureStatus}`}>
          <span className="stage-number">01</span>
          <strong>Filings &amp; Metrics</strong>
          <StatusBadge status={captureStatus} />
          <small>
            {run.evidence?.length || 0} evidence · {run.calculations?.length || 0} calcs
          </small>
        </div>
        <div className={`stage-card ${reportStage?.status || ''}`}>
          <span className="stage-number">02</span>
          <strong>Quick Brief Synthesis</strong>
          <StatusBadge status={reportStage?.status || 'pending'} />
          {reportStage && <small>Attempt {reportStage.attempt}</small>}
        </div>
      </div>
    );
  }

  return (
    <div className="stage-grid" aria-label="Research stage progress">
      {deepStages.map((name, i) => {
        const stage = run.stages?.filter((s) => s.stage === name).at(-1);
        return (
          <div key={name} className={`stage-card ${stage?.status || ''}`}>
            <span className="stage-number">0{i + 1}</span>
            <strong>{name === 'estimates' ? 'Expectations' : name[0].toUpperCase() + name.slice(1)}</strong>
            <StatusBadge status={stage?.status || 'pending'} />
            {stage && <small>Attempt {stage.attempt}</small>}
          </div>
        );
      })}
    </div>
  );
}
