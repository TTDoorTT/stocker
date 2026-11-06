import type { ReactNode } from 'react';
import type { Mode } from '../types';
export function ModeBadge({ mode }: { mode?: Mode }) {
  return (
    <span className={`badge ${mode === 'live' ? 'live' : 'fixture'}`}>
      {mode === 'live' ? 'Live provider data' : 'Demo · synthetic fixtures'}
    </span>
  );
}
export function StatusBadge({ status }: { status: string }) {
  return <span className={`badge status-${status}`}>{status.replaceAll('_', ' ')}</span>;
}
export function PageTitle({
  eyebrow,
  title,
  children,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
}) {
  return (
    <header className="page-title">
      <div>
        <p className="eyebrow">{eyebrow || 'STOCKSCOPE / U.S. MARKETS'}</p>
        <h1>{title}</h1>
      </div>
      {children}
    </header>
  );
}
export function SourceLink({ url, name, className }: { url: string; name: string; className?: string }) {
  return /^https?:\/\//i.test(url) ? (
    <a className={className} href={url} target="_blank" rel="noreferrer">
      {name} ↗
    </a>
  ) : (
    <span className={className}>{name}</span>
  );
}
