import { useEffect, useRef, useState } from 'react';
import { Navigate, Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import './App.css';
import { AdminPanel } from './components/AdminPanel';
import { AuthModal } from './components/AuthModal';
import CollectionCard from './components/CollectionCard';
import CollectionPage from './components/CollectionPage';
import ProfilePage from './components/ProfilePage';
import CreateCollectionModal from './components/CreateCollectionModal';
import LanguageFilter from './components/LanguageFilter';
import Pagination from './components/Pagination';
import { SettingsModal } from './components/SettingsModal';
import CodeSnippet from './components/CodeSnippet';
import CreateSnippetModal from './components/CreateSnippetModal';
import SearchBar from './components/SearchBar';
import { ChevronDownIcon, LogOutIcon, MoonIcon, SunIcon, UserIcon } from './components/Icons';
import { useSnippets } from './hooks/useSnippets';
import { useCollections } from './hooks/useCollections';
import { useLanguages } from './hooks/useLanguages';
import { useSearch } from './hooks/useSearch';
import { useTheme } from './hooks/useTheme';
import { useAuth } from './hooks/useAuth';

type HomeView = 'snippets' | 'collections';

export default function App() {
  const auth = useAuth();
  const {
    snippets,
    loading,
    error,
    page: snippetsPage,
    total: snippetsTotal,
    limit: snippetsLimit,
    setPage: setSnippetsPage,
    language: snippetsLanguage,
    setLanguage: setSnippetsLanguage,
    addSnippet,
    handleCopy,
    handleDelete,
    handleEdit,
    handleToggleVisibility,
  } = useSnippets(auth.token);
  const {
    collections,
    loading: collectionsLoading,
    error: collectionsError,
    page: collectionsPage,
    total: collectionsTotal,
    limit: collectionsLimit,
    setPage: setCollectionsPage,
    refreshCollections,
    addCollection,
    handleDelete: handleDeleteCollection,
    handleEdit: handleEditCollection,
    handleToggleVisibility: handleToggleCollectionVisibility,
  } = useCollections(auth.token);
  const languages = useLanguages(auth.token);
  const search = useSearch(handleCopy, auth.token);
  const { theme, toggleTheme } = useTheme();
  const [homeView, setHomeView] = useState<HomeView>('snippets');
  const [showCreate, setShowCreate] = useState(false);
  const [showCreateCollection, setShowCreateCollection] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [userDropdownOpen, setUserDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setUserDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  if (loading) {
    return (
      <div id="app-shell">
        <header className="app-header">
          <div className="header-inner">
            <span className="app-logo">Snippet <span>Finder</span></span>
            <div className="search-wrap">
              <div className="skeleton skeleton-search" />
            </div>
          </div>
        </header>
        <div className="snippet-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="skeleton-card">
              <div className="skeleton-card-header">
                <div className="skeleton skeleton-badge" />
                <div className="skeleton skeleton-title" />
              </div>
              <div className="skeleton skeleton-code" />
              <div className="skeleton-card-footer">
                <div className="skeleton skeleton-tag" />
                <div className="skeleton skeleton-tag" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div id="app-shell">
        <header className="app-header">
          <div className="header-inner">
            <span className="app-logo">Snippet <span>Finder</span></span>
          </div>
        </header>
        <div className="error-state">
          <p className="error-state-icon">!</p>
          <p className="error-state-title">Failed to load snippets</p>
          <p className="error-state-detail">{error}</p>
          <button className="snippet-btn snippet-btn--primary" onClick={() => window.location.reload()}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div id="app-shell">
      <header className="app-header">
        <div className="header-inner">
          <span className="app-logo">
            Snippet <span>Finder</span>
          </span>
          <SearchBar {...search} />

          {location.pathname === '/' && homeView === 'snippets' && (
            <button
              className="header-add-btn"
              onClick={() => setShowCreate(true)}
              disabled={!auth.user}
              title={auth.user ? 'Add snippet' : 'Log in to add snippets'}
            >
              <span className="header-add-btn-text">Add Snippet</span>
              <span className="header-add-btn-icon">+</span>
            </button>
          )}

          {location.pathname === '/' && homeView === 'collections' && (
            <button
              className="header-add-btn"
              onClick={() => setShowCreateCollection(true)}
              disabled={!auth.user}
              title={auth.user ? 'Add collection' : 'Log in to add collections'}
            >
              <span className="header-add-btn-text">Add Collection</span>
              <span className="header-add-btn-icon">+</span>
            </button>
          )}

          {auth.user?.role === 'admin' && (
            <button
              className={`header-admin-btn${location.pathname === '/admin' ? ' header-admin-btn--active' : ''}`}
              onClick={() => navigate(location.pathname === '/admin' ? '/' : '/admin')}
            >
              Admin
            </button>
          )}

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

      <Routes>
        <Route path="/" element={
          <>
            <div className="view-tabs">
              <button
                className={`view-tab${homeView === 'snippets' ? ' view-tab--active' : ''}`}
                onClick={() => setHomeView('snippets')}
              >
                Snippets
              </button>
              <button
                className={`view-tab${homeView === 'collections' ? ' view-tab--active' : ''}`}
                onClick={() => setHomeView('collections')}
              >
                Collections
              </button>
            </div>

            {homeView === 'snippets' && (
              <LanguageFilter
                languages={languages}
                value={snippetsLanguage}
                onChange={setSnippetsLanguage}
              />
            )}

            {homeView === 'snippets' ? (
              <>
                <div className="snippet-grid">
                  {snippets.map(snippet => (
                    <CodeSnippet
                      key={snippet.id}
                      snippet={snippet}
                      token={auth.token || undefined}
                      currentUserId={auth.user?.id || null}
                      canEdit={Boolean(auth.user && (snippet.owner_id === auth.user.id || auth.user.role === 'admin'))}
                      onCopy={handleCopy}
                      onDelete={handleDelete}
                      onEdit={handleEdit}
                      onToggleVisibility={handleToggleVisibility}
                      onCollectionChanged={refreshCollections}
                    />
                  ))}
                </div>
                <Pagination
                  page={snippetsPage}
                  total={snippetsTotal}
                  perPage={snippetsLimit}
                  onChange={setSnippetsPage}
                />
              </>
            ) : collectionsLoading ? (
              <div className="snippet-grid">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="skeleton-card">
                    <div className="skeleton-card-header">
                      <div className="skeleton skeleton-badge" />
                      <div className="skeleton skeleton-title" />
                    </div>
                    <div className="skeleton skeleton-code" />
                    <div className="skeleton-card-footer">
                      <div className="skeleton skeleton-tag" />
                    </div>
                  </div>
                ))}
              </div>
            ) : collectionsError ? (
              <div className="error-state">
                <p className="error-state-icon">!</p>
                <p className="error-state-title">Failed to load collections</p>
                <p className="error-state-detail">{collectionsError}</p>
                <button className="snippet-btn snippet-btn--primary" onClick={() => window.location.reload()}>
                  Retry
                </button>
              </div>
            ) : (
              <>
                <div className="collection-grid">
                  {collections.map(col => (
                    <CollectionCard
                      key={col.id}
                      collection={col}
                      currentUser={auth.user}
                      onDelete={handleDeleteCollection}
                      onEdit={handleEditCollection}
                      onToggleVisibility={handleToggleCollectionVisibility}
                    />
                  ))}
                </div>
                <Pagination
                  page={collectionsPage}
                  total={collectionsTotal}
                  perPage={collectionsLimit}
                  onChange={setCollectionsPage}
                />
              </>
            )}
          </>
        } />
        <Route path="/collections/:id" element={
          <CollectionPage
            currentUser={auth.user}
            token={auth.token || undefined}
            onCollectionChanged={refreshCollections}
          />
        } />
        <Route path="/users/:username" element={<ProfilePage />} />
        <Route path="/admin" element={
          auth.user?.role === 'admin'
            ? <AdminPanel token={auth.token || ''} currentUserId={auth.user.id} onBack={() => navigate('/')} />
            : <Navigate to="/" replace />
        } />
      </Routes>

      {showCreate && (
        <CreateSnippetModal
          token={auth.token || ''}
          onClose={() => setShowCreate(false)}
          onCreate={snippet => { addSnippet(snippet); setShowCreate(false); }}
        />
      )}

      {showCreateCollection && (
        <CreateCollectionModal
          token={auth.token || ''}
          onClose={() => setShowCreateCollection(false)}
          onCreate={col => { addCollection(col); setShowCreateCollection(false); }}
        />
      )}

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
