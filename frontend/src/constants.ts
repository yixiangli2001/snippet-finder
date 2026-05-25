export const API = 'http://127.0.0.1:8000';

export const LANGUAGES = [
  'BASH', 'C', 'C++', 'C#', 'CSS', 'DART', 'DOCKER',
  'GO', 'GRAPHQL', 'HTML', 'JAVA', 'JAVASCRIPT', 'JSON',
  'KOTLIN', 'LUA', 'MARKDOWN', 'MATLAB', 'PHP', 'PYTHON',
  'R', 'RUBY', 'RUST', 'SCALA', 'SQL', 'SWIFT',
  'TERRAFORM', 'TYPESCRIPT', 'YAML',
] as const;

export type Language = typeof LANGUAGES[number];
