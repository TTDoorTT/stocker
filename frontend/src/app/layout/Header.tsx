import { StockSearch } from '../../features/market/components/StockSearch';
export function Header({ error }: { error: boolean }) {
  return (
    <header className="topbar">
      <StockSearch />
      <div className="topbar-status">
        <span className={`connection-dot ${error ? 'offline' : ''}`} />
        {error ? 'API unavailable' : 'Local workspace'}
      </div>
    </header>
  );
}
