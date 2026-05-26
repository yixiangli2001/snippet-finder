import { useEffect, useState } from 'react';
import { API } from '../constants';
import { authHeaders } from '../utils/auth';

export function useLanguages(token: string | null) {
  const [languages, setLanguages] = useState<string[]>([]);

  useEffect(() => {
    async function fetchLanguages() {
      try {
        const res = await fetch(`${API}/snippets/languages`, {
          headers: authHeaders(token),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: string[] = await res.json();
        setLanguages(data);
      } catch {
        setLanguages([]);
      }
    }

    fetchLanguages();
  }, [token]);

  return languages;
}
