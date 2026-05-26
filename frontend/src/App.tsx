import { useEffect, useRef, useState } from 'react';
import { Navigate, NavLink, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import './App.css';
import { AdminPanel } from './components/AdminPanel';
import { AuthModal } from './components/AuthModal';
import CollectionPage from './components/CollectionPage';
import CollectionsPage from './components/CollectionsPage';
import ProfilePage from './components/ProfilePage';
import { SettingsModal } from './components/SettingsModal';
import SnippetsPage from './components/SnippetsPage';
import SearchBar from './components/SearchBar';
import { ChevronDownIcon, LogOutIcon, MoonIcon, SunIcon, UserIcon } from './components/Icons';
import { useSearch } from './hooks/useSearch';
import { useTheme } from './hooks/useTheme';
import { useAuth } from './hooks/useAuth';
import { API } from './constants';

// Routes on which the Snippets / Collections nav tabs are shown
const HOME_PATHS = ['/snippets', '/collections'];

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
  const [showSettings, setShowSettings] = useState(false);
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

  const isHomePath = HOME_PATHS.includes(location.pathname);

  return (
    <div id="app-shell">

      {/* ── Sticky header ───────────────────────────────────── */}
      <header className="app-header">
        <div className="header-inner">
          <span className="app-logo">
            Snippet <span>Finder</span>
          </span>

          {/* Global snippet search */}
          <SearchBar {...search} />

          {/* Admin toggle — only visible to users with the admin role */}
          {auth.user?.role === 'admin' && (
            <button
              className={`header-admin-btn${location.pathname === '/admin' ? ' header-admin-btn--active' : ''}`}
              onClick={() => navigate(location.pathname === '/admin' ? '/snippets' : '/admin')}
            >
              Admin
            </button>
          )}

          {/* User dropdown (logged in) or Log in button (logged out).
              Waits for auth to resolve before rendering to avoid a flash. */}
          {!auth.loadingUser && (
            auth.user ? (
              <div className="user-dropdown-wrap" ref={dropdownRef}>
                <button
                  className="header-user-btn"
                  onClick={() => setUserDropdownOpen(!userDropdownOpen)}
                  aria-expanded={userDropdownOpen}
                >
                  <span className="header-user-btn-name">{auth.user.username}</span>
                  <span className="header-user-btn-chevron">
                    <ChevronDownIcon />
                  </span>
                </button>
                {userDropdownOpen && (
                  <div className="user-dropdown">
                    <button
                      className="user-dropdown-item"
                      onClick={() => { setShowSettings(true); setUserDropdownOpen(false); }}
                    >
                      <UserIcon /> Account Settings
                    </button>
                    <div className="user-dropdown-divider" />
                    <button
                      className="user-dropdown-item user-dropdown-item--danger"
                      onClick={() => { auth.logout(); setUserDropdownOpen(false); }}
                    >
                      <LogOutIcon /> Logout
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button className="header-auth-btn" onClick={() => setShowAuth(true)}>Log in</button>
            )
          )}

          <button
            className="theme-toggle"
            onClick={toggleTheme}
            aria-label="Toggle theme"
            title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          >
            {theme === 'light' ? <MoonIcon /> : <SunIcon />}
          </button>
        </div>
      </header>

      {/* Nav tabs — shown only on the two main content pages */}
      {isHomePath && (
        <nav className="view-tabs">
          <NavLink
            to="/snippets"
            className={({ isActive }) => `view-tab${isActive ? ' view-tab--active' : ''}`}
          >
            Snippets
          </NavLink>
          <NavLink
            to="/collections"
            className={({ isActive }) => `view-tab${isActive ? ' view-tab--active' : ''}`}
          >
            Collections
          </NavLink>
        </nav>
      )}

      {/* ── Routes ──────────────────────────────────────────── */}
      <Routes>
        {/* Root redirects to snippets */}
        <Route path="/" element={<Navigate to="/snippets" replace />} />

        {/* Main content pages — each owns its own data and Add button */}
        <Route path="/snippets" element={<SnippetsPage />} />
        <Route path="/collections" element={<CollectionsPage />} />

        {/* Detail and profile pages */}
        <Route path="/collections/:id" element={
          <CollectionPage
            currentUser={auth.user}
            token={auth.token || undefined}
            onCollectionChanged={() => {}}
          />
        } />
        <Route path="/users/:username" element={<ProfilePage />} />

        {/* Admin panel — redirects non-admins to snippets */}
        <Route path="/admin" element={
          auth.user?.role === 'admin'
            ? <AdminPanel token={auth.token || ''} currentUserId={auth.user.id} onBack={() => navigate('/snippets')} />
            : <Navigate to="/snippets" replace />
        } />
      </Routes>

      {/* ── Site-wide modals (auth state, not page state) ────── */}
      {showAuth && (
        <AuthModal
          onLogin={auth.login}
          onRegister={auth.register}
          onClose={() => setShowAuth(false)}
        />
      )}

      {showSettings && auth.user && (
        <SettingsModal
          user={auth.user}
          onUpdateProfile={auth.updateProfile}
          onUpdatePassword={auth.updatePassword}
          onDeleteAccount={auth.deleteAccount}
          onClose={() => setShowSettings(false)}
        />
      )}

    </div>
  );
}
