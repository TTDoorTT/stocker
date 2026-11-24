import { useState } from 'react';
import { Link } from 'react-router-dom';
import { useResource } from '../../../shared/hooks/useResource';
import { Empty, ErrorBox, Loading } from '../../../shared/ui/Feedback';
import { ModeBadge, PageTitle, StatusBadge } from '../../../shared/ui/Presentation';
import { dateTime } from '../../../shared/utils/format';
import { researchApi } from '../api';

export function ResearchRecords() {
  const records = useResource(researchApi.runs);
  const [deletingId, setDeletingId] = useState('');
  const [actionError, setActionError] = useState('');

  async function removeRun(runId: string) {
    setDeletingId(runId);
    setActionError('');
    try {
      await researchApi.deleteRun(runId);
      records.reload();
    } catch (e) {
      setActionError(e instanceof Error ? e.message : 'Research record could not be deleted');
    } finally {
      setDeletingId('');
    }
  }

  return (
    <>
      <PageTitle title="Research records">
        <Link className="button" to="/research">
          New research ↗
        </Link>
      </PageTitle>
      <p className="muted">
        Saved runs retain stage attempts, evidence, calculation inputs and validation failures.
      </p>
      {actionError && <ErrorBox message={actionError} />}
      <section className="panel">
        {records.loading ? (
          <Loading />
        ) : records.error ? (
          <ErrorBox message={records.error} retry={records.reload} />
        ) : records.data?.length ? (
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Started</th>
                  <th>Model / data</th>
                  <th>Status</th>
                  <th>Record</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {records.data.map((run) => {
                  const active = ['queued', 'running'].includes(run.status);
                  return (
                    <tr key={run.run_id}>
                      <td>
                        <strong>{run.symbol}</strong>
                      </td>
                      <td>{dateTime(run.started_at)}</td>
                      <td>
                        {run.model_id}
                        <br />
                        <ModeBadge mode={run.mode} />
                      </td>
                      <td>
                        <StatusBadge status={run.status} />
                      </td>
                      <td>
                        <Link to={`/runs/${run.run_id}`}>Open analysis ↗</Link>
                      </td>
                      <td>
                        <button
                          type="button"
                          className="link-button danger-link"
                          aria-label={`Delete ${run.symbol} research record`}
                          disabled={active || deletingId === run.run_id}
                          title={active ? 'Stop active research run before deleting' : undefined}
                          onClick={() => void removeRun(run.run_id)}
                        >
                          {deletingId === run.run_id ? 'Deleting…' : 'Delete'}
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty>No research runs yet. Open a stock and start Deep Research.</Empty>
        )}
      </section>
    </>
  );
}
