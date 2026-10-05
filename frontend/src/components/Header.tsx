import { Link, useLocation } from 'react-router-dom';
import { useApiHealth } from '../hooks/useApiHealth';

export function Header() {
  const location = useLocation();
  const apiStatus = useApiHealth();

  const isActive = (path: string) =>
    location.pathname === path ? 'active' : '';

  return (
    <header className="app-header">
      <div className="app-header__left">
        <Link to="/" className="app-header__logo" aria-label="BUGSLASH home">
          BUG<span>SLASH</span>
        </Link>
        <nav className="app-header__nav" aria-label="Main navigation">
          <Link to="/" className={isActive('/')}>
            Dashboard
          </Link>
          <Link to="/scans" className={isActive('/scans')}>
            Scans
          </Link>
        </nav>
      </div>
      <div className="app-header__right">
        <div className="api-status" aria-live="polite">
          <span
            className={`api-status__dot api-status__dot--${apiStatus}`}
            role="status"
          />
          <span>
            API{' '}
            {apiStatus === 'connected'
              ? 'Connected'
              : apiStatus === 'offline'
                ? 'Disconnected'
                : 'Checking...'}
          </span>
        </div>
      </div>
    </header>
  );
}
