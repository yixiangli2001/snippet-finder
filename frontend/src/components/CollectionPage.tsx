import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { API } from '../constants';
import { authHeaders } from '../utils/auth';
import { type Collection } from '../types/collection';
import { type Snippet } from './CodeSnippet';
import CodeSnippet from './CodeSnippet';

interface Props {
  currentUserId: string | null;
  token?: string;
  onCollectionChanged?: () => void;
}

export default function CollectionPage({ currentUserId, token, onCollectionChanged }: Props) {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [collection, setCollection] = useState<Collection | null>(null);
  const [snippets, setSnippets] = useState<Snippet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    async function fetchCollection() {
      setLoading(true);
      setError(null);
      setSnippets([]);
      try {
        const colRes = await fetch(`${API}/collections/${id}`, { headers: authHeaders(token ?? null) });
        if (!colRes.ok) throw new Error(`HTTP ${colRes.status}`);
        const col: Collection = await colRes.json();
        setCollection(col);

        if (col.snippet_ids.length > 0) {
          const snips: Snippet[] = [];
          for (const snippetId of col.snippet_ids) {
            try {
              const snippetRes = await fetch(`${API}/snippets/${snippetId}`, { headers: authHeaders(token ?? null) });
              if (snippetRes.ok) {
                const snippet: Snippet = await snippetRes.json();
                snips.push(snippet);
              }
            } catch {
              // Skip if snippet fetch fails
            }
          }
          setSnippets(snips);
        }
      } catch (err) {
        setError((err as Error).message);
      } finally {
        setLoading(false);
      }
    }

    fetchCollection();
  }, [id, token]);

  async function handleRemoveSnippet(snippetId: string) {
    if (!id) return;
    try {
      const res = await fetch(`${API}/collections/${id}/snippets/${snippetId}`, {
        method: 'DELETE',
        headers: authHeaders(token ?? null),
      });
      if (!res.ok) throw new Error('Failed to remove snippet');
      setSnippets(prev => prev.filter(s => s.id !== snippetId));
      setCollection(prev => prev ? { ...prev, snippet_ids: prev.snippet_ids.filter(sid => sid !== snippetId) } : null);
      onCollectionChanged?.();
    } catch (err) {
      setError((err as Error).message);
    }
  }

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

  if (error || !collection) {
    return (
      <div className="error-state">
        <p className="error-state-icon">!</p>
        <p className="error-state-title">Failed to load collection</p>
        <p className="error-state-detail">{error}</p>
        <button className="snippet-btn snippet-btn--primary" onClick={() => navigate('/')}>
          Back to home
        </button>
      </div>
    );
  }

  const isOwner = currentUserId && collection.owner_id === currentUserId;

  return (
    <div className="collection-page-wrap">
      <div className="collection-page-header">
        <button className="collection-page-back" onClick={() => navigate('/')}>
          ← Back
        </button>
        <h1 className="collection-page-title">{collection.name}</h1>
        {collection.description && (
          <p className="collection-page-desc">{collection.description}</p>
        )}
        <div className="collection-page-meta">
          {collection.owner_username && (
            <span className="collection-page-owner">by {collection.owner_username}</span>
          )}
          <span className={`snippet-visibility${collection.is_public ? ' snippet-visibility--public' : ''}`}>
            {collection.is_public ? 'Public' : 'Private'}
          </span>
        </div>
      </div>

      {snippets.length === 0 ? (
        <div className="empty-state">
          <p className="empty-state-icon">∅</p>
          <p className="empty-state-title">No snippets in this collection</p>
        </div>
      ) : (
        <div className="snippet-grid">
          {snippets.map(snippet => (
            <CodeSnippet
              key={snippet.id}
              snippet={snippet}
              token={token}
              canEdit={Boolean(currentUserId && snippet.owner_id === currentUserId)}
              onCopy={() => {}}
              onRemove={isOwner ? handleRemoveSnippet : undefined}
              onCollectionChanged={onCollectionChanged}
            />
          ))}
        </div>
      )}
    </div>
  );
}
