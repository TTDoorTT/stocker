import { StatusBadge } from '../../../shared/ui/Presentation';
import type { Run } from '../types';

const stages = ['profile', 'financials', 'estimates', 'valuation', 'risk', 'report'];
export function AgentProgress({ run }: { run: Run }) {
  return (
    <div className="stage-grid" aria-label="Research stage progress">
      {stages.map((name, i) => {
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
