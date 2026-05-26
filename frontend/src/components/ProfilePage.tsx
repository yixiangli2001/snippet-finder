import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './CollectionPage.css';
import './ProfilePage.css';
import { useAuth } from '../hooks/useAuth';
import { authHeaders } from '../utils/auth';
import { API } from '../constants';
import { type Snippet } from '../types/snippet';
import { type Collection } from '../types/collection';
import CodeSnippet from './CodeSnippet';
import CollectionCard from './CollectionCard';

export default function ProfilePage() {
  const { username } = useParams<{ username: string }>();
  const navigate = useNavigate();
  const { user, token } = useAuth();

  const [resolvedUsername, setResolvedUsername] = useState('');
  const [profileOwnerId, setProfileOwnerId] = useState('');
  const [snippets, setSnippets] = useState<Snippet[]>([]);
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!username) return;

    async function fetchProfile() {
      setLoading(true);
      setNotFound(false);
      setError(null);
      try {
        // Resolve username → id (case-insensitive on the backend)
        const userRes = await fetch(`${API}/users/${encodeURIComponent(username!)}`);
        if (userRes.status === 404) { setNotFound(true); return; }
        if (!userRes.ok) throw new Error(`HTTP ${userRes.status}`);
        const owner: { id: string; username: string } = await userRes.json();
        setResolvedUsername(owner.username);
        setProfileOwnerId(owner.id);

        // Pass auth token so the backend shows private content to the owner or admin
        const headers = authHeaders(token);
        const [snippetsRes, collectionsRes] = await Promise.all([
          fetch(`${API}/snippets/?owner_id=${owner.id}&limit=100`, { headers }),
          fetch(`${API}/collections/?owner_id=${owner.id}&limit=100`, { headers }),
        ]);
        if (!snippetsRes.ok) throw new Error(`HTTP ${snippetsRes.status}`);
        if (!collectionsRes.ok) throw new Error(`HTTP ${collectionsRes.status}`);

        const snippetsData: { items: Snippet[] } = await snippetsRes.json();
        const collectionsData: { items: Collection[] } = await collectionsRes.json();
        setSnippets(snippetsData.items);
        setCollections(collectionsData.items);
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    }

    fetchProfile();
  }, [username, token]);

  // Owner or admin can perform CRUD actions on this profile's content
  const canEdit = Boolean(user && (user.id === profileOwnerId || user.role === 'admin'));

  // ── Snippet handlers ───────────────────────────────────────
  function handleCopy(id: string) {
    fetch(`${API}/snippets/${id}/copy`, { method: 'PATCH' }).catch(() => {});
    setSnippets(prev => prev.map(s => s.id === id ? { ...s, times_copied: s.times_copied + 1 } : s));
  }

  async function handleDeleteSnippet(id: string) {
    setSnippets(prev => prev.filter(s => s.id !== id));
    await fetch(`${API}/snippets/${id}`, { method: 'DELETE', headers: authHeaders(token) });
  }

  async function handleEditSnippet(id: string, updates: Partial<Snippet>) {
    const res = await fetch(`${API}/snippets/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error('Update failed');
    const updated: Snippet = await res.json();
    setSnippets(prev => prev.map(s => s.id === id ? updated : s));
  }

  async function handleToggleSnippetVisibility(id: string) {
    const res = await fetch(`${API}/snippets/${id}/visibility`, {
      method: 'PATCH',
      headers: authHeaders(token),
    });
    if (!res.ok) throw new Error('Visibility update failed');
    const updated: Snippet = await res.json();
    setSnippets(prev => prev.map(s => s.id === id ? updated : s));
  }

  // ── Collection handlers ────────────────────────────────────
  async function handleDeleteCollection(id: string) {
    setCollections(prev => prev.filter(c => c.id !== id));
    await fetch(`${API}/collections/${id}`, { method: 'DELETE', headers: authHeaders(token) });
  }

  async function handleEditCollection(id: string, updates: { name?: string; description?: string | null }) {
    const res = await fetch(`${API}/collections/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error('Update failed');
    const updated: Collection = await res.json();
    setCollections(prev => prev.map(c => c.id === id ? updated : c));
  }

  async function handleToggleCollectionVisibility(id: string) {
    const col = collections.find(c => c.id === id);
    if (!col) return;
    const res = await fetch(`${API}/collections/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify({ is_public: !col.is_public }),
    });
    if (!res.ok) throw new Error('Visibility update failed');
    const updated: Collection = await res.json();
    setCollections(prev => prev.map(c => c.id === id ? updated : c));
  }

  if (loading) {
    return (
      <div className="profile-page">
        <div className="collection-page-header">
          <button className="collection-page-back" onClick={() => navigate('/')}>← Back</button>
          <div className="skeleton" style={{ height: 28, width: 160, borderRadius: 6 }} />
        </div>
        <div className="snippet-grid">
          {Array.from({ length: 4 }).map((_, i) => (
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
      </div>
    );
  }

  if (notFound) {
    return (
      <div className="profile-page">
        <div className="error-state">
          <p className="error-state-icon">?</p>
          <p className="error-state-title">User not found</p>
          <p className="error-state-detail">No account with the username "{username}".</p>
          <button className="snippet-btn snippet-btn--primary" onClick={() => navigate('/')}>
            Back to home
          </button>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="profile-page">
        <div className="error-state">
          <p className="error-state-icon">!</p>
          <p className="error-state-title">Failed to load profile</p>
          <p className="error-state-detail">{error}</p>
          <button className="snippet-btn snippet-btn--primary" onClick={() => navigate('/')}>
            Back to home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="profile-page">
      <div className="collection-page-header">
        <button className="collection-page-back" onClick={() => navigate('/')}>← Back</button>
        <h1 className="profile-username">{resolvedUsername}</h1>
      </div>

      <section className="profile-section">
        <h2 className="profile-section-title">Snippets</h2>
        {snippets.length === 0 ? (
          <p className="profile-empty">No snippets yet.</p>
        ) : (
          <div className="snippet-grid">
            {snippets.map(snippet => (
              <CodeSnippet
                key={snippet.id}
                snippet={snippet}
                token={token || undefined}
                currentUserId={user?.id || null}
                canEdit={canEdit}
                onCopy={handleCopy}
                onDelete={handleDeleteSnippet}
                onEdit={handleEditSnippet}
                onToggleVisibility={handleToggleSnippetVisibility}
                onCollectionChanged={() => {}}
              />
            ))}
          </div>
        )}
      </section>

      <section className="profile-section">
        <h2 className="profile-section-title">Collections</h2>
        {collections.length === 0 ? (
          <p className="profile-empty">No collections yet.</p>
        ) : (
          <div className="collection-grid">
            {collections.map(col => (
              <CollectionCard
                key={col.id}
                collection={col}
                currentUser={canEdit ? user : null}
                onDelete={handleDeleteCollection}
                onEdit={handleEditCollection}
                onToggleVisibility={handleToggleCollectionVisibility}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
