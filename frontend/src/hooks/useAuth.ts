import { useState } from 'react';
import { API } from '../constants';
import {
  authHeaders,
  clearStoredAuth,
  getStoredToken,
  getStoredUser,
  storeToken,
  storeUser,
  type User,
} from '../utils/auth';

export function useAuth() {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [user, setUser] = useState<User | null>(() => getStoredUser());

  async function loadUser(nextToken: string) {
    const res = await fetch(`${API}/users/me`, { headers: authHeaders(nextToken) });
    if (!res.ok) throw new Error('Session expired');
    const profile: User = await res.json();
    storeUser(profile);
    setUser(profile);
  }

  async function login(email: string, password: string) {
    const res = await fetch(`${API}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) throw new Error('Login failed');
    const body: { access_token: string } = await res.json();
    storeToken(body.access_token);
    setToken(body.access_token);
    await loadUser(body.access_token);
  }

  async function register(email: string, username: string, password: string) {
    const res = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, username, password }),
    });
    if (!res.ok) throw new Error('Registration failed');
    await login(email, password);
  }

  function logout() {
    clearStoredAuth();
    setToken(null);
    setUser(null);
  }

  return { token, user, loadingUser: Boolean(token && !user), login, register, logout };
}
