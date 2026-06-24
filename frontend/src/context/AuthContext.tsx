import { createContext, useContext, useState, type ReactNode } from 'react';
import { API } from '../constants';
import {
  authHeaders,
  clearStoredAuth,
  getStoredToken,
  getStoredUser,
  storeToken,
  storeUser,
  throwHttpError,
  type User,
} from '../utils/auth';

interface AuthContextValue {
  token: string | null;
  user: User | null;
  loadingUser: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string, turnstileToken: string) => Promise<void>;
  logout: () => void;
  updateProfile: (updates: { email?: string; username?: string }) => Promise<void>;
  updatePassword: (oldPassword: string, newPassword: string) => Promise<void>;
  deleteAccount: () => Promise<void>;
  verifyEmail: (token: string) => Promise<void>;
  resendVerification: (email: string) => Promise<void>;
  forgotPassword: (email: string, turnstileToken: string) => Promise<void>;
  resetPassword: (token: string, newPassword: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
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
    if (!res.ok) await throwHttpError(res, 'Login failed');
    const body: { access_token: string } = await res.json();
    storeToken(body.access_token);
    setToken(body.access_token);
    await loadUser(body.access_token);
  }

  // Does not log the user in — the account is unverified until they click
  // the link emailed to them, and login is blocked until then.
  async function register(email: string, username: string, password: string, turnstileToken: string) {
    const res = await fetch(`${API}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, username, password, turnstile_token: turnstileToken }),
    });
    if (!res.ok) await throwHttpError(res, 'Registration failed');
  }

  async function verifyEmail(token: string) {
    const res = await fetch(`${API}/auth/verify-email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });
    if (!res.ok) await throwHttpError(res, 'Verification failed');
  }

  async function resendVerification(email: string) {
    const res = await fetch(`${API}/auth/resend-verification`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (!res.ok) await throwHttpError(res, 'Failed to resend verification email');
  }

  async function forgotPassword(email: string, turnstileToken: string) {
    const res = await fetch(`${API}/auth/forgot-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, turnstile_token: turnstileToken }),
    });
    if (!res.ok) await throwHttpError(res, 'Request failed');
  }

  async function resetPassword(token: string, newPassword: string) {
    const res = await fetch(`${API}/auth/reset-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword }),
    });
    if (!res.ok) await throwHttpError(res, 'Password reset failed');
  }

  function logout() {
    clearStoredAuth();
    setToken(null);
    setUser(null);
  }

  async function updateProfile(updates: { email?: string; username?: string }) {
    let latest: User | null = null;

    if (updates.username && updates.username !== user?.username) {
      const res = await fetch(`${API}/users/me/username`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ username: updates.username }),
      });
      if (!res.ok) await throwHttpError(res, 'Failed to update username');
      latest = await res.json();
    }

    if (updates.email && updates.email !== user?.email) {
      const res = await fetch(`${API}/users/me/email`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
        body: JSON.stringify({ email: updates.email }),
      });
      if (!res.ok) await throwHttpError(res, 'Failed to update email');
      latest = await res.json();
    }

    if (latest) {
      storeUser(latest);
      setUser(latest);
    }
  }

  async function updatePassword(oldPassword: string, newPassword: string) {
    const res = await fetch(`${API}/users/me/password`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', ...authHeaders(token) },
      body: JSON.stringify({ current_password: oldPassword, new_password: newPassword }),
    });
    if (!res.ok) await throwHttpError(res, 'Failed to update password');
  }

  async function deleteAccount() {
    const res = await fetch(`${API}/users/me`, {
      method: 'DELETE',
      headers: authHeaders(token),
    });
    if (!res.ok) throw new Error('Failed to delete account');
    clearStoredAuth();
    setToken(null);
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{
      token,
      user,
      loadingUser: Boolean(token && !user),
      login,
      register,
      logout,
      updateProfile,
      updatePassword,
      deleteAccount,
      verifyEmail,
      resendVerification,
      forgotPassword,
      resetPassword,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuthContext(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuthContext must be used inside <AuthProvider>');
  return ctx;
}
