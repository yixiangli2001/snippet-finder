import { useState } from 'react';
import './App.css';
import CodeSnippet from './components/CodeSnippet';
import CreateSnippetModal from './components/CreateSnippetModal';
import SearchBar from './components/SearchBar';
import { MoonIcon, SunIcon } from './components/Icons';
import { useSnippets } from './hooks/useSnippets';
import { useSearch } from './hooks/useSearch';
import { useTheme } from './hooks/useTheme';

export default function App() {
  const { snippets, loading, error, addSnippet, handleCopy, handleDelete, handleEdit } = useSnippets();
  const search = useSearch(handleCopy);
  const { theme, toggleTheme } = useTheme();
  const [showCreate, setShowCreate] = useState(false);

  if (loading) {
    return (
      <div id="app-shell">
        <header className="app-header">
          <span className="app-logo">Snippet <span>Finder</span></span>
          <div className="search-wrap">
            <div className="skeleton skeleton-search" />
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
          <span className="app-logo">Snippet <span>Finder</span></span>
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
        <span className="app-logo">
          Snippet <span>Finder</span>
        </span>
        <SearchBar {...search} />
        <button className="header-add-btn" onClick={() => setShowCreate(true)}>
          <span className="header-add-btn-text">Add Snippet</span>
          <span className="header-add-btn-icon">+</span>
        </button>
        <button
          className="theme-toggle"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
          title={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}
        >
          {theme === 'light' ? <MoonIcon /> : <SunIcon />}
        </button>
      </header>

      <div className="snippet-grid">
        {snippets.map((snippet) => (
          <CodeSnippet
            key={snippet.id}
            snippet={snippet}
            onCopy={handleCopy}
            onDelete={handleDelete}
            onEdit={handleEdit}
          />
        ))}
      </div>

      {showCreate && (
        <CreateSnippetModal
          onClose={() => setShowCreate(false)}
          onCreate={(snippet) => {
            addSnippet(snippet);
            setShowCreate(false);
          }}
        />
      )}
    </div>
  );
}
