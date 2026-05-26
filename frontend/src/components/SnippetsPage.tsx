import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useSnippets } from '../hooks/useSnippets';
import { useLanguages } from '../hooks/useLanguages';
import CodeSnippet from './CodeSnippet';
import LanguageFilter from './LanguageFilter';
import Pagination from './Pagination';
import CreateSnippetModal from './CreateSnippetModal';

export default function SnippetsPage() {
  const { user, token } = useAuth();
  const {
    snippets, loading, error,
    page, total, limit, setPage,
    language, setLanguage,
    addSnippet, handleCopy, handleDelete, handleEdit, handleToggleVisibility,
  } = useSnippets(token);
  const languages = useLanguages(token);
  const [showCreate, setShowCreate] = useState(false);

  if (loading) {
    return (
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
    );
  }

  if (error) {
    return (
      <div className="error-state">
        <p className="error-state-icon">!</p>
        <p className="error-state-title">Failed to load snippets</p>
        <p className="error-state-detail">{error}</p>
        <button className="snippet-btn snippet-btn--primary" onClick={() => window.location.reload()}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <>
      {/* Toolbar: language filter on the left, Add button on the right */}
      <div className="page-toolbar">
        <LanguageFilter languages={languages} value={language} onChange={setLanguage} />
        {user && (
          <button
            className="snippet-btn snippet-btn--primary"
            onClick={() => setShowCreate(true)}
          >
            + Add Snippet
          </button>
        )}
      </div>

      <div className="snippet-grid">
        {snippets.map(snippet => (
          <CodeSnippet
            key={snippet.id}
            snippet={snippet}
            token={token || undefined}
            currentUserId={user?.id || null}
            canEdit={Boolean(user && (snippet.owner_id === user.id || user.role === 'admin'))}
            onCopy={handleCopy}
            onDelete={handleDelete}
            onEdit={handleEdit}
            onToggleVisibility={handleToggleVisibility}
            onCollectionChanged={() => {}}
          />
        ))}
      </div>

      <Pagination page={page} total={total} perPage={limit} onChange={setPage} />

      {showCreate && (
        <CreateSnippetModal
          token={token || ''}
          onClose={() => setShowCreate(false)}
          onCreate={snippet => { addSnippet(snippet); setShowCreate(false); }}
        />
      )}
    </>
  );
}
