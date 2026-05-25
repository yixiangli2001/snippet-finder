import { useEffect, useState } from 'react';
import { API } from '../constants';
import { authHeaders } from '../utils/auth';
import { type Collection } from '../types/collection';

interface Props {
  snippetId: string;
  token: string;
  currentUserId: string;
  onClose: () => void;
  onSuccess: () => void;
}

export default function AddToCollectionModal({ snippetId, token, currentUserId, onClose, onSuccess }: Props) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [selectedId, setSelectedId] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [adding, setAdding] = useState(false);

  useEffect(() => {
    async function fetchCollections() {
      try {
        const res = await fetch(`${API}/collections/`, { headers: authHeaders(token) });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const cols: Collection[] = await res.json();
        const ownedCollections = cols.filter(col => col.owner_id === currentUserId);
        setCollections(ownedCollections);
        if (ownedCollections.length > 0) setSelectedId(ownedCollections[0].id);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    }
    fetchCollections();
  }, [token, currentUserId]);

  async function handleAdd() {
    if (!selectedId) return;
    setAdding(true);
    setError('');
    try {
      const res = await fetch(`${API}/collections/${selectedId}/snippets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ snippet_id: snippetId }),
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.detail || `HTTP ${res.status}`);
      }
      onSuccess();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setAdding(false);
    }
  }

  return (
    <div className="overlay-backdrop" onClick={onClose}>
      <div className="overlay-panel" onClick={e => e.stopPropagation()}>
        <h2 className="overlay-title">Add to Collection</h2>
        {loading ? (
          <p className="overlay-loading">Loading collections…</p>
        ) : collections.length === 0 ? (
          <div className="overlay-empty-wrap">
            <p className="overlay-empty">No collections yet. Create your first collection to organize snippets.</p>
            <div className="snippet-edit-actions">
              <button className="snippet-btn snippet-btn--ghost" onClick={onClose}>
                Close
              </button>
            </div>
          </div>
        ) : (
          <form className="overlay-form" onSubmit={e => { e.preventDefault(); handleAdd(); }}>
            <div className="snippet-field">
              <select
                className="snippet-edit-input snippet-edit-select"
                value={selectedId}
                onChange={e => setSelectedId(e.target.value)}
                autoFocus
              >
                {collections.map(col => (
                  <option key={col.id} value={col.id}>
                    {col.name} ({col.snippet_ids.length} snippets)
                  </option>
                ))}
              </select>
            </div>
            {error && <span className="auth-error">{error}</span>}
            <div className="snippet-edit-actions">
              <button type="button" className="snippet-btn snippet-btn--ghost" onClick={onClose}>
                Cancel
              </button>
              <button type="submit" className="snippet-btn snippet-btn--primary" disabled={adding}>
                {adding ? 'Adding…' : 'Add to Collection'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
