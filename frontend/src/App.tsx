import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import './App.css';
import { AdminPanel } from './components/AdminPanel';
import { AuthModal } from './components/AuthModal';
import CollectionPage from './components/CollectionPage';
import CollectionsPage from './components/CollectionsPage';
import ProfilePage from './components/ProfilePage';
import SettingsPage from './components/SettingsPage';
import SnippetsPage from './components/SnippetsPage';
import SearchBar from './components/SearchBar';
import { ChevronDownIcon, CodeIcon, FolderIcon, GearIcon, MoonIcon, SunIcon, UserIcon } from './components/Icons';
import { useSearch } from './hooks/useSearch';
import { useTheme } from './hooks/useTheme';
import { useAuth } from './hooks/useAuth';
import { API } from './constants';


export default function App() {
  // ── Data hooks ─────────────────────────────────────────────
  const auth = useAuth();
  // Search lives in the header; it only needs to fire the copy PATCH,
  // not sync with the snippets page state.
  const handleSearchCopy = (id: string) => {
    fetch(`${API}/snippets/${id}/copy`, { method: 'PATCH' }).catch(() => {});
  };
  const search = useSearch(handleSearchCopy, auth.token);
  const { theme, toggleTheme } = useTheme();

  // ── UI state ───────────────────────────────────────────────
  const [showAuth, setShowAuth] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const location = useLocation();

  // Close the user dropdown when the user clicks anywhere outside it
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setUserDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <div id="app-shell">

      {/* ── Integrated Bento Header ─────────────────────────── */}
      <header className="app-header">
        <div className="header-inner">
          <Link to="/" className="app-logo">
            Snippet <span>Finder</span>
          </Link>

          {/* Primary navigation — always visible */}
          <nav className="header-nav">
            <NavLink
              to="/snippets"
              className={({ isActive }) => `nav-link${isActive ? ' nav-link--active' : ''}`}
            >
              Snippets
            </NavLink>
            <NavLink
              to="/collections"
              className={({ isActive }) => `nav-link${isActive ? ' nav-link--active' : ''}`}
            >
              Collections
            </NavLink>
          </nav>

          <SearchBar {...search} />

          <div className="header-actions">
            {/* Manage (admin only) — gear icon signals configuration, not identity */}
            {auth.user?.role === 'admin' && (
              <button
                className={`action-btn action-btn--labeled${location.pathname === '/admin' ? ' action-btn--active' : ''}`}
                onClick={() => navigate(location.pathname === '/admin' ? '/snippets' : '/admin')}
                title="Manage"
              >
                <GearIcon />
                <span className="action-btn-text">Manage</span>
              </button>
            )}

            {/* User controls */}
            {!auth.loadingUser && (
              auth.user ? (
                <div className="user-dropdown-wrap" ref={dropdownRef}>
                  <button
                    className="user-btn"
                    onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                    aria-expanded={userDropdownOpen}
                  >
                    <UserIcon />
                    <span className="user-btn-name">{auth.user.username}</span>
                    <ChevronDownIcon />
                  </button>
                  {userDropdownOpen && (
                    <div className="user-dropdown">
                      <button
                        className="user-dropdown-item"
                        onClick={() => { navigate('/settings'); setUserDropdownOpen(false); }}
                      >
                        Account Settings
                      </button>
                      <button
                        className="user-dropdown-item"
                        onClick={() => { navigate(`/users/${auth.user!.username}`); setUserDropdownOpen(false); }}
                      >
                        My Profile
                      </button>
                      <div className="user-dropdown-divider" />
                      <button
                        className="user-dropdown-item user-dropdown-item--danger"
                        onClick={() => { auth.logout(); setUserDropdownOpen(false); }}
                      >
                        Log out
                      </button>
                    </div>
                  )}
                </div>
              ) : (
                <button className="auth-trigger-btn" onClick={() => setShowAuth(true)}>Log in</button>
              )
            )}

            <button
              className="theme-btn"
              onClick={toggleTheme}
              aria-label="Toggle theme"
            >
              {theme === 'light' ? <MoonIcon /> : <SunIcon />}
            </button>
          </div>
        </div>
      </header>

      {/* ── Routes (width-constrained by page-wrap) ─────────── */}
      <div className="page-wrap">
      <Routes>
        <Route path="/" element={<Navigate to="/snippets" replace />} />
        <Route path="/snippets" element={<SnippetsPage />} />
        <Route path="/collections" element={<CollectionsPage />} />
        <Route path="/collections/:id" element={
          <CollectionPage
            currentUser={auth.user}
            token={auth.token || undefined}
            onCollectionChanged={() => {}}
          />
        } />
        <Route path="/users/:username" element={<ProfilePage />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/admin" element={
          auth.user?.role === 'admin'
            ? <AdminPanel token={auth.token || ''} currentUserId={auth.user.id} onBack={() => navigate('/snippets')} />
            : <Navigate to="/snippets" replace />
        } />
      </Routes>
      </div>

      {/* ── Auth modal — outside page-wrap, not width-clipped ── */}
      {showAuth && (
        <AuthModal
          onLogin={auth.login}
          onRegister={auth.register}
          onClose={() => setShowAuth(false)}
        />
      )}

      {/* ── Mobile bottom tab bar (≤520px only, via CSS) ──────── */}
      <nav className="bottom-nav" aria-label="Main navigation">
        <NavLink
          to="/snippets"
          className={({ isActive }) => `bottom-nav-link${isActive ? ' bottom-nav-link--active' : ''}`}
        >
          <CodeIcon />
          <span>Snippets</span>
        </NavLink>
        <NavLink
          to="/collections"
          className={({ isActive }) => `bottom-nav-link${isActive ? ' bottom-nav-link--active' : ''}`}
        >
          <FolderIcon />
          <span>Collections</span>
        </NavLink>
      </nav>

    </div>
  );
}
