import { useState } from 'react';
import { API } from '../constants';
import { authHeaders } from '../utils/auth';
import { type Collection } from '../types/collection';

interface Props {
  token: string;
  onClose: () => void;
  onCreate: (collection: Collection) => void;
}

export default function CreateCollectionModal({ token, onClose, onCreate }: Props) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) { setError('Name is required'); return; }
    setSaving(true);
    setError('');
    try {
      const res = await fetch(`${API}/collections/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ name: name.trim(), description: description.trim() || null }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const created: Collection = await res.json();
      onCreate(created);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="overlay-backdrop" onClick={onClose}>
      <div className="overlay-panel" onClick={e => e.stopPropagation()}>
        <h2 className="overlay-title">New Collection</h2>
        <form className="overlay-form" onSubmit={handleSubmit}>
          <input
            className="auth-input auth-input--full"
            placeholder="Name *"
            value={name}
            onChange={e => { setName(e.target.value); setError(''); }}
            autoFocus
            required
          />
          <textarea
            className="snippet-edit-textarea"
            placeholder="Description (optional)"
            rows={2}
            value={description}
            onChange={e => setDescription(e.target.value)}
          />
          {error && <span className="auth-error">{error}</span>}
          <div className="snippet-edit-actions">
            <button type="button" className="snippet-btn snippet-btn--ghost" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="snippet-btn snippet-btn--primary" disabled={saving}>
              {saving ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
