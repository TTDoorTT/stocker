import { StockSearch } from '../../features/market/components/StockSearch';

type Theme = 'dark' | 'light';

type HeaderProps = {
  error: boolean;
  theme: Theme;
  onToggleTheme: () => void;
};

export function Header({ error, theme, onToggleTheme }: HeaderProps) {
  const label = theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme';
  return (
    <header className="topbar">
      <StockSearch />
      <div className="topbar-actions">
        <div className="topbar-status">
          <span className={`connection-dot ${error ? 'offline' : ''}`} />
          {error ? 'API unavailable' : 'Local workspace'}
        </div>
        <button
          type="button"
          className="theme-toggle"
          onClick={onToggleTheme}
          aria-label={label}
          title={label}
        >
          {theme === 'dark' ? (
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <circle cx="12" cy="12" r="4" />
              <path d="M12 2v2m0 16v2M2 12h2m16 0h2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41m0-14.14-1.41 1.41M6.34 17.66l-1.41 1.41" />
            </svg>
          ) : (
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M20.9 13.1A9 9 0 0 1 10.9 3.1a9 9 0 1 0 10 10Z" />
            </svg>
          )}
        </button>
      </div>
    </header>
  );
}
