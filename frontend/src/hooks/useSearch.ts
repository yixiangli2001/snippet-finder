import { useEffect, useRef, useState } from 'react';
import { API } from '../constants';
import { type Snippet } from '../components/CodeSnippet';

export function useSearch(onCopy: (id: string) => void) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Snippet[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Debounced search fetch
  useEffect(() => {
    const trimmedQuery = query.trim();
    if (!trimmedQuery) {
      return;
    }
    const debounceTimer = setTimeout(async () => {
      try {
        const res = await fetch(`${API}/snippets/?search=${encodeURIComponent(trimmedQuery)}`);
        if (!res.ok) return;
        const data: Snippet[] = await res.json();
        setResults(data);
        setIsOpen(true);
        setSelectedIdx(-1);
      } catch {
        // silently ignore transient search errors
      }
    }, 300);
    return () => clearTimeout(debounceTimer);
  }, [query]);

  function updateQuery(nextQuery: string) {
    setQuery(nextQuery);
    if (!nextQuery.trim()) {
      setResults([]);
      setIsOpen(false);
      setSelectedIdx(-1);
    }
  }

  function copyResult(snippet: Snippet) {
    navigator.clipboard.writeText(snippet.code);
    onCopy(snippet.id);
    setIsOpen(false);
    setQuery('');
    inputRef.current?.blur();
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (!isOpen || results.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const target = selectedIdx >= 0 ? results[selectedIdx] : results[0];
      if (target) copyResult(target);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
      setQuery('');
      inputRef.current?.blur();
    }
  }

  function onFocus() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    if (query.trim() && results.length > 0) setIsOpen(true);
  }

  // Delayed close so a mousedown on a result fires before the input loses focus
  function onBlur() {
    closeTimer.current = setTimeout(() => setIsOpen(false), 150);
  }

  function cancelClose() {
    if (closeTimer.current) clearTimeout(closeTimer.current);
  }

  return {
    query, setQuery: updateQuery,
    results, isOpen,
    selectedIdx, setSelectedIdx,
    inputRef,
    copyResult, onKeyDown, onFocus, onBlur, cancelClose,
  };
}
