const TOKEN_KEY = 'snippet_finder_token';
const USER_KEY = 'snippet_finder_user';

export interface User {
  id: string;
  email: string;
  username: string;
  role: string;
}

export function getStoredToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  return raw ? JSON.parse(raw) as User : null;
}

export function storeToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function storeUser(user: User) {
  localStorage.setItem(USER_KEY, JSON.stringify(user));
}

export function clearStoredAuth() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function authHeaders(token: string | null): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// Carries the HTTP status alongside the message so callers can branch on it
// (e.g. distinguishing a 403 "verify your email" login failure from a 401).
export class HttpError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export async function throwHttpError(res: Response, fallback: string): Promise<never> {
  const body = await res.json().catch(() => ({}));
  const detail = Array.isArray(body.detail) ? body.detail[0]?.msg : body.detail;
  throw new HttpError(detail || fallback, res.status);
}
