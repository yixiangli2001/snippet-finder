import { useState } from 'react';
import { type Collection } from '../types/collection';
import { type User } from '../utils/auth';

interface Props {
  collection: Collection;
  currentUser: User | null;
  onDelete: (id: string) => void;
  onEdit: (id: string, updates: { name?: string; description?: string | null }) => Promise<void>;
  onToggleVisibility: (id: string) => void;
}

export default function CollectionCard({ collection, currentUser, onDelete, onEdit, onToggleVisibility }: Props) {
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState(collection.name);
  const [editDesc, setEditDesc] = useState(collection.description ?? '');
  const [saving, setSaving] = useState(false);

  const isOwner = currentUser && collection.owner_id === currentUser.id;
  const snippetCount = collection.snippet_ids.length;

  async function handleEditSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!editName.trim()) return;
    setSaving(true);
    try {
      await onEdit(collection.id, {
        name: editName.trim(),
        description: editDesc.trim() || null,
      });
      setIsEditing(false);
    } finally {
      setSaving(false);
    }
  }

  if (isEditing) {
    return (
      <div className="collection-card">
        <form className="collection-card-edit" onSubmit={handleEditSubmit}>
          <input
            className="auth-input auth-input--full"
            value={editName}
            onChange={e => setEditName(e.target.value)}
            autoFocus
            required
          />
          <textarea
            className="snippet-edit-textarea"
            rows={2}
            value={editDesc}
            onChange={e => setEditDesc(e.target.value)}
            placeholder="Description (optional)"
          />
          <div className="snippet-edit-actions">
            <button type="button" className="snippet-btn snippet-btn--ghost" onClick={() => setIsEditing(false)}>
              Cancel
            </button>
            <button type="submit" className="snippet-btn snippet-btn--primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </form>
      </div>
    );
  }

  return (
    <div className="collection-card">
      <div className="collection-card-header">
        <div className="collection-card-meta">
          <span className={`snippet-visibility${collection.is_public ? ' snippet-visibility--public' : ''}`}>
            {collection.is_public ? 'Public' : 'Private'}
          </span>
          <span className="collection-snippet-count">
            {snippetCount} {snippetCount === 1 ? 'snippet' : 'snippets'}
          </span>
        </div>
        {isOwner && (
          <div className="collection-card-actions" onClick={e => e.stopPropagation()}>
            <button
              className="snippet-action-btn"
              onClick={() => onToggleVisibility(collection.id)}
            >
              {collection.is_public ? 'Make private' : 'Make public'}
            </button>
            <button className="snippet-action-btn" onClick={() => setIsEditing(true)}>
              Edit
            </button>
            {confirmingDelete ? (
              <>
                <button
                  className="snippet-action-btn snippet-action-btn--delete"
                  onClick={() => onDelete(collection.id)}
                >
                  Confirm
                </button>
                <button className="snippet-action-btn" onClick={() => setConfirmingDelete(false)}>
                  Cancel
                </button>
              </>
            ) : (
              <button
                className="snippet-action-btn snippet-action-btn--delete"
                onClick={() => setConfirmingDelete(true)}
              >
                Delete
              </button>
            )}
          </div>
        )}
      </div>

      <h2 className="collection-card-name">{collection.name}</h2>
      {collection.description && (
        <p className="collection-card-desc">{collection.description}</p>
      )}

      {collection.owner_username && (
        <div className="collection-card-footer">
          <span className="collection-owner-text">{collection.owner_username}</span>
        </div>
      )}
    </div>
  );
}
