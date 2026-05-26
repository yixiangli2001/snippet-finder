import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { API } from '../constants';
import { type Snippet } from './CodeSnippet';
import { type Collection } from '../types/collection';
import CodeSnippet from './CodeSnippet';
import CollectionCard from './CollectionCard';

export default function ProfilePage() {
  const { username } = useParams<{ username: string }>();
  const navigate = useNavigate();
  const [resolvedUsername, setResolvedUsername] = useState('');
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
        const userRes = await fetch(`${API}/users/${encodeURIComponent(username)}`);
        if (userRes.status === 404) { setNotFound(true); return; }
        if (!userRes.ok) throw new Error(`HTTP ${userRes.status}`);
        const user: { id: string; username: string } = await userRes.json();
        setResolvedUsername(user.username);

        // Fetch public snippets and collections in parallel
        // Note: trailing slash on /snippets/ avoids a 307 redirect
        const [snippetsRes, collectionsRes] = await Promise.all([
          fetch(`${API}/snippets/?owner_id=${user.id}&limit=100`),
          fetch(`${API}/collections/?owner_id=${user.id}&limit=100`),
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
  }, [username]);

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
          <p className="profile-empty">No public snippets yet.</p>
        ) : (
          <div className="snippet-grid">
            {snippets.map(snippet => (
              <CodeSnippet
                key={snippet.id}
                snippet={snippet}
                canEdit={false}
                onCopy={() => {}}
              />
            ))}
          </div>
        )}
      </section>

      <section className="profile-section">
        <h2 className="profile-section-title">Collections</h2>
        {collections.length === 0 ? (
          <p className="profile-empty">No public collections yet.</p>
        ) : (
          <div className="collection-grid">
            {collections.map(col => (
              <CollectionCard
                key={col.id}
                collection={col}
                currentUser={null}
                onDelete={() => {}}
                onEdit={async () => {}}
                onToggleVisibility={() => {}}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
