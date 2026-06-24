// In production, set VITE_API_URL to your deployed backend (e.g. on Render).
// Falls back to the local dev server when the variable is not set.
export const API = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000';

export const LANGUAGES = [
  'BASH', 'C', 'C++', 'C#', 'CSS', 'DART', 'DOCKER',
  'GO', 'GRAPHQL', 'HTML', 'JAVA', 'JAVASCRIPT', 'JSON',
  'KOTLIN', 'LUA', 'MARKDOWN', 'MATLAB', 'PHP', 'PYTHON',
  'R', 'RUBY', 'RUST', 'SCALA', 'SQL', 'SWIFT',
  'TERRAFORM', 'TYPESCRIPT', 'YAML',
] as const;

export type Language = typeof LANGUAGES[number];
