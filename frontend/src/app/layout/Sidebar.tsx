import { useEffect, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { isIndustryResearchHidden, WORKSPACE_PREFS_EVENT } from '../preferences';

const navigation = [
  ['/', '◈', 'Home'],
  ['/intelligence', '⌁', 'Industry Intelligence'],
  ['/industries', '▦', 'Industry Research'],
  ['/research', '⌕', 'Stock Research'],
  ['/my-stocks', '☆', 'My Stocks'],
  ['/records', '▤', 'Research Records'],
  ['/settings', '⚙', 'Settings / AI'],
];

export function Sidebar() {
  const [hideIndustryResearch, setHideIndustryResearch] = useState(isIndustryResearchHidden);

  useEffect(() => {
    const sync = () => setHideIndustryResearch(isIndustryResearchHidden());
    window.addEventListener(WORKSPACE_PREFS_EVENT, sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener(WORKSPACE_PREFS_EVENT, sync);
      window.removeEventListener('storage', sync);
    };
  }, []);

  const items = hideIndustryResearch ? navigation.filter(([path]) => path !== '/industries') : navigation;

  return (
    <aside className="sidebar">
      <NavLink className="brand" to="/">
        <span className="brand-mark">S</span>
        <span>
          Stocker
          <small>RESEARCH WORKSPACE</small>
        </span>
      </NavLink>
      <p className="sidebar-label">WORKSPACE</p>
      <nav aria-label="Main navigation">
        {items.map(([path, icon, label]) => (
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
