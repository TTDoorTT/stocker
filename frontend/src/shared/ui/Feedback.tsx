import type { ReactNode } from 'react';
export function ErrorBox({ message, retry }: { message: string; retry?: () => void }) {
  return (
    <div role="alert" className="notice error">
      <strong>Unable to complete request</strong>
      <p>{message}</p>
      {retry && (
        <button className="button secondary" onClick={retry}>
          Try again
        </button>
      )}
    </div>
  );
}
export function Empty({ children }: { children: ReactNode }) {
  return <div className="empty">{children}</div>;
}
export function Loading() {
  return (
    <div className="empty" role="status">
      <span className="spinner" /> Loading sourced data…
    </div>
  );
}
export function Gaps({ gaps }: { gaps?: unknown[] }) {
  if (!gaps?.length) return null;
  return (
    <div className="notice">
      <strong>Data limitations</strong>
      <ul>
        {gaps.map((gap, i) => (
          <li key={i}>{typeof gap === 'string' ? gap : JSON.stringify(gap)}</li>
        ))}
      </ul>
    </div>
  );
}
