import { NavLink } from 'react-router-dom';

const navigation = [
  ['/', '◈', 'Home'],
  ['/daily-review', '◷', 'Daily Review'],
  ['/intelligence', '⌁', 'Industry Intelligence'],
  ['/industries', '▦', 'Industry Research'],
  ['/research', '⌕', 'Stock Research'],
  ['/my-stocks', '☆', 'My Stocks'],
  ['/records', '▤', 'Research Records'],
  ['/settings', '⚙', 'Settings / AI'],
];
export function Sidebar() {
  return (
    <aside className="sidebar">
      <NavLink className="brand" to="/">
        <span className="brand-mark">S</span>
        <span>
          StockScope<span className="brand-ai"> AI</span>
          <small>RESEARCH WORKSPACE</small>
        </span>
      </NavLink>
      <p className="sidebar-label">WORKSPACE</p>
      <nav aria-label="Main navigation">
        {navigation.map(([path, icon, label]) => (
          <NavLink key={path} to={path} end={path === '/'}>
            <span aria-hidden="true">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <span className="connection-dot" /> Local research environment
        <p>
          Educational research.
          <br />
          Not investment advice.
        </p>
      </div>
    </aside>
  );
}
