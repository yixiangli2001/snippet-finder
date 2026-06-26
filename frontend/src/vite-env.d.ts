/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Base URL of the backend API. Unset in local dev → defaults to http://127.0.0.1:8000. */
  readonly VITE_API_URL?: string;
  /** Cloudflare Turnstile site key. Unset → defaults to Cloudflare's "always passes" test key. */
  readonly VITE_TURNSTILE_SITE_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
