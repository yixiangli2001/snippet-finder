import { useEffect, useRef, useState } from 'react';
import { API } from '../constants';
import { type Snippet } from '../types/snippet';
import { authHeaders } from '../utils/auth';

const LIMIT = 9;

// Checks if the current snippet values match the optimistic values for all fields being updated. 
function valuesMatch(current: Snippet, optimistic: Snippet, updated: Partial<Snippet>) {
  return Object.keys(updated).every((key) => {
    const field = key as keyof Snippet;
    const currentValue = current[field];
    const optimisticValue = optimistic[field];

    if (Array.isArray(currentValue) && Array.isArray(optimisticValue)) {
      return currentValue.length === optimisticValue.length
        && currentValue.every((value, index) => value === optimisticValue[index]);
    }

    return currentValue === optimisticValue;
  });
}

export function useSnippets(token: string | null) {
  const [snippets, setSnippets] = useState<Snippet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [language, setLanguageState] = useState('');
  const prevToken = useRef(token);

  // Reset to page 1 when the user logs in or out
  useEffect(() => {
    if (prevToken.current !== token) {
      prevToken.current = token;
      setPage(1);
      setLanguageState('');
    }
  }, [token]);

  function setLanguage(lang: string) {
    setLanguageState(lang);
    setPage(1);
  }

  useEffect(() => {
    setLoading(true);
    setError(null);
    const skip = (page - 1) * LIMIT;
    const langParam = language ? `&language=${encodeURIComponent(language)}` : '';
    fetch(`${API}/snippets?skip=${skip}&limit=${LIMIT}${langParam}`, { headers: authHeaders(token) })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: { items: Snippet[]; total: number }) => {
        setSnippets(data.items);
        setTotal(data.total);
      })
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, [token, page, language]);

  function addSnippet(snippet: Snippet) {
    setSnippets((prev) => [snippet, ...prev]);
    setTotal((prev) => prev + 1);
  }

  function handleCopy(id: string) {
    fetch(`${API}/snippets/${id}/copy`, { method: 'PATCH' }).catch(() => {});
    setSnippets((prev) =>
      prev.map((s) => (s.id === id ? { ...s, times_copied: s.times_copied + 1 } : s))
    );
  }

  async function handleDelete(id: string) {
    const removedIndex = snippets.findIndex((s) => s.id === id);
    if (removedIndex === -1) return;
    const removedSnippet = snippets[removedIndex];

    setSnippets((prev) => prev.filter((s) => s.id !== id));
    setTotal((prev) => prev - 1);

    try {
      const res = await fetch(`${API}/snippets/${id}`, {
        method: 'DELETE',
        headers: authHeaders(token),
      });
      if (!res.ok) throw new Error(`Delete failed (HTTP ${res.status})`);
    } catch (err) {
      setSnippets((prev) => {
        if (prev.some((s) => s.id === removedSnippet.id)) return prev;
        const next = [...prev];
        next.splice(Math.min(removedIndex, next.length), 0, removedSnippet);
        return next;
      });
      setTotal((prev) => prev + 1);
      alert((err as Error).message);
    }
  }

  async function handleEdit(id: string, updated: Partial<Snippet>) {
    const previousSnippet = snippets.find((s) => s.id === id);
    if (!previousSnippet) return;
    const optimisticSnippet = { ...previousSnippet, ...updated };

    setSnippets((prev) => prev.map((s) => (s.id === id ? optimisticSnippet : s)));

    try {
      const res = await fetch(`${API}/snippets/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify(updated),
      });
      if (!res.ok) throw new Error(`Update failed (HTTP ${res.status})`);
    } catch (err) {
      setSnippets((prev) =>
        prev.map((s) => {
          if (s.id !== id) return s;
          return valuesMatch(s, optimisticSnippet, updated) ? previousSnippet : s;
        })
      );
      alert((err as Error).message);
    }
  }

  async function handleToggleVisibility(id: string) {
    const previousSnippet = snippets.find((s) => s.id === id);
    if (!previousSnippet) return;
    const optimisticSnippet = { ...previousSnippet, is_public: !previousSnippet.is_public };

    setSnippets((prev) => prev.map((s) => (s.id === id ? optimisticSnippet : s)));

    try {
      const res = await fetch(`${API}/snippets/${id}/visibility`, {
        method: 'PATCH',
        headers: authHeaders(token),
      });
      if (!res.ok) throw new Error(`Visibility update failed (HTTP ${res.status})`);
      const updatedSnippet: Snippet = await res.json();
      setSnippets((prev) => prev.map((s) => (s.id === id ? updatedSnippet : s)));
    } catch (err) {
      setSnippets((prev) => prev.map((s) => (s.id === id ? previousSnippet : s)));
      alert((err as Error).message);
    }
  }

  return {
    snippets, loading, error,
    page, total, limit: LIMIT, setPage,
    language, setLanguage,
    addSnippet, handleCopy, handleDelete, handleEdit, handleToggleVisibility,
  };
}
