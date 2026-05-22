import { useState } from 'react';
import './App.css';
import { AuthModal } from './components/AuthModal';
import CodeSnippet from './components/CodeSnippet';
import CreateSnippetModal from './components/CreateSnippetModal';
import SearchBar from './components/SearchBar';
import { MoonIcon, SunIcon } from './components/Icons';
import { useSnippets } from './hooks/useSnippets';
import { useSearch } from './hooks/useSearch';
import { useTheme } from './hooks/useTheme';
import { useAuth } from './hooks/useAuth';

export default function App() {
  const auth = useAuth();
  const {
    snippets,
    loading,
    error,
    addSnippet,
    handleCopy,
    handleDelete,
    handleEdit,
    handleToggleVisibility,
  } = useSnippets(auth.token);
  const search = useSearch(handleCopy, auth.token);
  const { theme, toggleTheme } = useTheme();
  const [showCreate, setShowCreate] = useState(false);
  const [showAuth, setShowAuth] = useState(false);

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
          <button
            className="header-add-btn"
            onClick={() => setShowCreate(true)}
            disabled={!auth.user}
            title={auth.user ? "Add snippet" : "Log in to add snippets"}
          >
            <span className="header-add-btn-text">Add Snippet</span>
            <span className="header-add-btn-icon">+</span>
          </button>

          {!auth.loadingUser && (
            auth.user ? (
              <div className="header-user-wrap">
                <span className="header-user-chip">{auth.user.username}</span>
                <button className="header-auth-btn" onClick={auth.logout}>Logout</button>
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

      <div className="snippet-grid">
        {snippets.map((snippet) => (
          <CodeSnippet
            key={snippet.id}
            snippet={snippet}
            canEdit={Boolean(auth.user && snippet.owner_id === auth.user.id)}
            onCopy={handleCopy}
            onDelete={handleDelete}
            onEdit={handleEdit}
            onToggleVisibility={handleToggleVisibility}
          />
        ))}
      </div>

      {showCreate && (
        <CreateSnippetModal
          token={auth.token || ''}
          onClose={() => setShowCreate(false)}
          onCreate={(snippet) => {
            addSnippet(snippet);
            setShowCreate(false);
          }}
        />
      )}

      {showAuth && (
        <AuthModal
          onLogin={auth.login}
          onRegister={auth.register}
          onClose={() => setShowAuth(false)}
        />
      )}
    </div>
  );
}
