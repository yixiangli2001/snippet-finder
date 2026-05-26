import { useCallback, useEffect, useState } from 'react';
import { API } from '../constants';
import { authHeaders, type User } from '../utils/auth';

export function useAdmin(token: string | null) {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/admin/users`, { headers: authHeaders(token) });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setUsers(await res.json());
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { fetchUsers(); }, [fetchUsers]);

  async function updateUser(userId: string, updates: { username?: string; email?: string }) {
    const res = await fetch(`${API}/admin/users/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify(updates),
    });
    if (!res.ok) {
      const data = await res.json();
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    const updated: User = await res.json();
    setUsers(prev => prev.map(u => u.id === userId ? updated : u));
  }

  async function deleteUser(userId: string) {
    const res = await fetch(`${API}/admin/users/${userId}`, {
      method: 'DELETE',
      headers: authHeaders(token),
    });
    if (!res.ok) throw new Error('Failed to delete user');
    setUsers(prev => prev.filter(u => u.id !== userId));
  }

  return { users, loading, error, updateUser, deleteUser };
}
