import { type ReactNode, useEffect, useState } from 'react';
import { useResource } from '../../shared/hooks/useResource';
import { ModeBadge } from '../../shared/ui/Presentation';
import { appApi } from '../api';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

type Theme = 'dark' | 'light';

function readTheme(): Theme {
  try {
    return window.localStorage.getItem('stocker-theme') === 'light' ? 'light' : 'dark';
  } catch {
    return 'dark';
  }
}

export function Shell({ children }: { children: ReactNode }) {
  const [theme, setTheme] = useState<Theme>(readTheme);
  const health = useResource(appApi.health);
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      window.localStorage.setItem('stocker-theme', theme);
    } catch {
      // The theme still works when browser storage is unavailable.
    }
  }, [theme]);
  useEffect(() => {
    window.addEventListener('ai-configuration-saved', health.reload);
    return () => window.removeEventListener('ai-configuration-saved', health.reload);
  }, [health.reload]);
  return (
    <div className="app-shell">
      <Sidebar />
      <div className="main-shell">
        <Header
          error={!!health.error}
          theme={theme}
          onToggleTheme={() => setTheme((current) => (current === 'dark' ? 'light' : 'dark'))}
        />
        <div className={`mode-banner ${health.data?.mode === 'live' ? 'live' : ''}`}>
          {health.error ? (
            <span>Backend unavailable. Start the local API to load data.</span>
          ) : health.loading ? (
            <span>Checking data mode…</span>
          ) : (
            <>
              <ModeBadge mode={health.data?.mode} />
              <span>
                {health.data?.mode === 'live'
                  ? 'Facts are returned by configured providers. Review timestamps and limitations.'
                  : 'Synthetic sample data and deterministic model outputs. No live financial claims.'}
              </span>
            </>
          )}
        </div>
        <main id="main-content">
          {children}
          <footer>
            Stocker · U.S. / Canadian research workspace <span>Sources before conclusions.</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
