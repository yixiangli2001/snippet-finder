import { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useCollections } from '../hooks/useCollections';
import CollectionCard from './CollectionCard';
import Pagination from './Pagination';
import CreateCollectionModal from './CreateCollectionModal';

export default function CollectionsPage() {
  const { user, token } = useAuth();
  const {
    collections, loading, error,
    page, total, limit, setPage,
    addCollection, handleDelete, handleEdit, handleToggleVisibility,
  } = useCollections(token);
  const [showCreate, setShowCreate] = useState(false);

  if (loading) {
    return (
      <div className="collection-grid">
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
    );
  }

  if (error) {
    return (
      <div className="error-state">
        <p className="error-state-icon">!</p>
        <p className="error-state-title">Failed to load collections</p>
        <p className="error-state-detail">{error}</p>
        <button className="snippet-btn snippet-btn--primary" onClick={() => window.location.reload()}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <>
      {/* Toolbar: Add button on the right */}
      {user && (
        <div className="page-toolbar page-toolbar--end">
          <button
            className="snippet-btn snippet-btn--primary"
            onClick={() => setShowCreate(true)}
          >
            + Add Collection
          </button>
        </div>
      )}

      <div className="collection-grid">
        {collections.map(col => (
          <CollectionCard
            key={col.id}
            collection={col}
            currentUser={user}
            onDelete={handleDelete}
            onEdit={handleEdit}
            onToggleVisibility={handleToggleVisibility}
          />
        ))}
      </div>

      <Pagination page={page} total={total} perPage={limit} onChange={setPage} />

      {showCreate && (
        <CreateCollectionModal
          token={token || ''}
          onClose={() => setShowCreate(false)}
          onCreate={col => { addCollection(col); setShowCreate(false); }}
        />
      )}
    </>
  );
}
