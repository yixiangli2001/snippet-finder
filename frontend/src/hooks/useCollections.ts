import { useEffect, useState } from 'react';
import { API } from '../constants';
import { authHeaders } from '../utils/auth';
import { type Collection } from '../types/collection';

export function useCollections(token: string | null) {
  const [collections, setCollections] = useState<Collection[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetch(`${API}/collections/`, { headers: authHeaders(token) })
      .then(res => { if (!res.ok) throw new Error(`HTTP ${res.status}`); return res.json(); })
      .then((data: Collection[]) => setCollections(data))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token]);

  function addCollection(col: Collection) {
    setCollections(prev => [col, ...prev]);
  }

  async function handleDelete(id: string) {
    setCollections(prev => prev.filter(c => c.id !== id));
    try {
      const res = await fetch(`${API}/collections/${id}`, {
        method: 'DELETE',
        headers: authHeaders(token),
      });
      if (!res.ok) throw new Error('Delete failed');
    } catch {
      // Re-fetch to restore state if delete failed
      const res = await fetch(`${API}/collections/`, { headers: authHeaders(token) });
      if (res.ok) setCollections(await res.json());
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

  return { collections, loading, error, addCollection, handleDelete, handleEdit, handleToggleVisibility };
}
