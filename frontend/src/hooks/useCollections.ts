import { useCallback, useEffect, useRef, useState } from 'react';
import { API } from '../constants';
import { authHeaders } from '../utils/auth';
import { type Collection } from '../types/collection';
import { type Scope, type Visibility } from './useSnippets';

const LIMIT = 9;

export function useCollections(token: string | null, currentUserId: string | null) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [scope, setScopeState] = useState<Scope>('all');
  const [visibility, setVisibilityState] = useState<Visibility>('all');
  const prevToken = useRef(token);

  // Reset filters and go back to page 1 when the user logs in or out
  useEffect(() => {
    if (prevToken.current !== token) {
      prevToken.current = token;
      setPage(1);
      setScopeState('all');
      setVisibilityState('all');
    }
  }, [token]);

  function setScope(next: Scope) {
    setScopeState(next);
    // Visibility only makes sense inside "mine"; reset it when leaving.
    if (next === 'all') setVisibilityState('all');
    setPage(1);
  }

  function setVisibility(next: Visibility) {
    setVisibilityState(next);
    setPage(1);
  }

  const refreshCollections = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams({
        skip: String((page - 1) * LIMIT),
        limit: String(LIMIT),
      });
      if (scope === 'mine' && currentUserId) params.set('owner_id', currentUserId);
      if (visibility !== 'all') params.set('is_public', String(visibility === 'public'));

      const res = await fetch(`${API}/collections/?${params.toString()}`, {
        headers: authHeaders(token),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: { items: Collection[]; total: number } = await res.json();
      setCollections(data.items);
      setTotal(data.total);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [token, currentUserId, page, scope, visibility]);

  useEffect(() => {
    refreshCollections();
  }, [refreshCollections]);

  function addCollection(col: Collection) {
    setCollections(prev => [col, ...prev]);
    setTotal(prev => prev + 1);
  }

  async function handleDelete(id: string) {
    setCollections(prev => prev.filter(c => c.id !== id));
    setTotal(prev => prev - 1);
    try {
      const res = await fetch(`${API}/collections/${id}`, {
        method: 'DELETE',
        headers: authHeaders(token),
      });
      if (!res.ok) throw new Error('Delete failed');
    } catch {
      await refreshCollections();
    }
  }

  async function handleEdit(id: string, updates: { name?: string; description?: string | null }) {
    const res = await fetch(`${API}/collections/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify(updates),
    });
    if (!res.ok) throw new Error('Failed to update collection');
    const updated: Collection = await res.json();
    setCollections(prev => prev.map(c => c.id === id ? updated : c));
  }

  async function handleToggleVisibility(id: string) {
    const previous = collections.find(c => c.id === id);
    if (!previous) return;
    const optimistic = { ...previous, is_public: !previous.is_public };
    setCollections(prev => prev.map(c => c.id === id ? optimistic : c));
    try {
      const res = await fetch(`${API}/collections/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ is_public: !previous.is_public }),
      });
      if (!res.ok) throw new Error('Failed');
      const updated: Collection = await res.json();
      setCollections(prev => prev.map(c => c.id === id ? updated : c));
    } catch {
      setCollections(prev => prev.map(c => c.id === id ? previous : c));
    }
  }

  return {
    collections, loading, error,
    page, total, limit: LIMIT, setPage,
    scope, setScope,
    visibility, setVisibility,
    refreshCollections, addCollection, handleDelete, handleEdit, handleToggleVisibility,
  };
}
