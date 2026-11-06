import type { Evidence } from '../types';
import { dateTime, formatNumber } from '../utils/format';
import { Empty } from './Feedback';
import { SourceLink } from './Presentation';
export function EvidenceTable({ evidence }: { evidence: Evidence[] }) {
  return evidence.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Evidence / field</th>
            <th>Value / unit</th>
            <th>Period</th>
            <th>Source & publication</th>
            <th>Retrieved</th>
          </tr>
        </thead>
        <tbody>
          {evidence.map((ev) => (
            <tr key={ev.evidence_id}>
              <td>
                <code>{ev.evidence_id}</code>
                <br />
                {ev.field.replaceAll('_', ' ')}
              </td>
              <td>
                {typeof ev.value === 'number' ? formatNumber(ev.value) : (ev.value ?? 'Unavailable')}{' '}
                {ev.unit}
                <small>{ev.currency}</small>
              </td>
              <td>{ev.period}</td>
              <td>
                <SourceLink url={ev.source_url} name={ev.source_name} />
                <small>{dateTime(ev.published_at)}</small>
              </td>
              <td>
                {dateTime(ev.fetched_at)}
                {ev.cached && <small>Cached provider response</small>}
                {ev.fixture && <small>Synthetic fixture</small>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty>No evidence available.</Empty>
  );
}
