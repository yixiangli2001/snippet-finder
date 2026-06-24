import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useSnippets } from '../hooks/useSnippets';
import { useLanguages } from '../hooks/useLanguages';
import CodeSnippet from './CodeSnippet';
import LanguageFilter from './LanguageFilter';
import SegmentedFilter from './SegmentedFilter';
import Pagination from './Pagination';
import CreateSnippetModal from './CreateSnippetModal';

export default function SnippetsPage() {
  const { user, token } = useAuth();
  const {
    snippets, loading, error,
    page, total, limit, setPage,
    language, setLanguage,
    scope, setScope,
    visibility, setVisibility,
    addSnippet, handleCopy, handleDelete, handleEdit, handleToggleVisibility,
  } = useSnippets(token, user?.id ?? null);
  const { languages, refreshLanguages } = useLanguages(token);
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

  // Tailor the empty message to the active filters so it explains *why* the list is empty.
  const emptyMessage = scope === 'mine'
    ? visibility === 'private' ? 'You have no private snippets.'
    : visibility === 'public' ? 'You have no public snippets.'
    : 'You have no snippets yet.'
    : 'No snippets found.';

  return (
    <>
      {/* Toolbar: scope/visibility + language filters on the left, Add button on the right */}
      <div className="page-toolbar">
        <div className="page-toolbar-filters">
          {user && (
            <SegmentedFilter
              label="Show snippets"
              value={scope}
              onChange={setScope}
              options={[
                { value: 'all', label: 'All' },
                { value: 'mine', label: 'Mine' },
              ]}
            />
          )}
          {user && scope === 'mine' && (
            <SegmentedFilter
              label="Filter by visibility"
              value={visibility}
              onChange={setVisibility}
              options={[
                { value: 'all', label: 'All' },
                { value: 'public', label: 'Public' },
                { value: 'private', label: 'Private' },
              ]}
            />
          )}
          <LanguageFilter languages={languages} value={language} onChange={setLanguage} />
        </div>
        {user && (
          <button
            className="snippet-btn snippet-btn--primary"
            onClick={() => setShowCreate(true)}
          >
            + Add Snippet
          </button>
        )}
      </div>

      {snippets.length === 0 ? (
        <p className="list-empty">{emptyMessage}</p>
      ) : (
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
      )}

      <Pagination page={page} total={total} perPage={limit} onChange={setPage} />

      {showCreate && (
        <CreateSnippetModal
          token={token || ''}
          onClose={() => setShowCreate(false)}
          onCreate={snippet => { addSnippet(snippet); refreshLanguages(); setShowCreate(false); }}
        />
      )}
    </>
  );
}
