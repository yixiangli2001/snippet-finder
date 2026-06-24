// In production, set VITE_API_URL to your deployed backend (e.g. on Render).
// Falls back to the local dev server when the variable is not set.
export const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

// Cloudflare Turnstile site key for the register / forgot-password widgets.
// Defaults to Cloudflare's official "always passes" test key, which pairs
// with the backend's default test secret — the app works end-to-end with
// no Cloudflare account. Set a real site key in production for real bot filtering.
export const TURNSTILE_SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY ?? '1x00000000000000000000AA';

export const LANGUAGES = [
  'BASH', 'C', 'C++', 'C#', 'CSS', 'DART', 'DOCKER',
  'GO', 'GRAPHQL', 'HTML', 'JAVA', 'JAVASCRIPT', 'JSON',
  'KOTLIN', 'LUA', 'MARKDOWN', 'MATLAB', 'PHP', 'PYTHON',
  'R', 'RUBY', 'RUST', 'SCALA', 'SQL', 'SWIFT',
  'TERRAFORM', 'TYPESCRIPT', 'YAML',
] as const;

export type Language = typeof LANGUAGES[number];
