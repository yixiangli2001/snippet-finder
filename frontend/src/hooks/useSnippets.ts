import { useEffect, useState } from 'react';
import { API } from '../constants';
import { type Snippet } from '../components/CodeSnippet';

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

export function useSnippets() {
  const [snippets, setSnippets] = useState<Snippet[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/snippets`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: Snippet[]) => setSnippets(data))
      .catch((err: Error) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  function addSnippet(snippet: Snippet) {
    setSnippets((prev) => [snippet, ...prev]);
  }

  function handleCopy(id: string) {
    // Fire-and-forget is acceptable for copy count — not critical data
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

    try {
      const res = await fetch(`${API}/snippets/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error(`Delete failed (HTTP ${res.status})`);
    } catch (err) {
      setSnippets((prev) => {
        if (prev.some((s) => s.id === removedSnippet.id)) return prev;
        const next = [...prev];
        next.splice(Math.min(removedIndex, next.length), 0, removedSnippet);
        return next;
      });
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
        headers: { 'Content-Type': 'application/json' },
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

  return { snippets, loading, error, addSnippet, handleCopy, handleDelete, handleEdit };
}
