/// <reference types="vite/client" />

interface ImportMetaEnv {
  /**
   * Optional. The base URL the API client prepends to every request.
   * Set at build time (`VITE_API_BASE_URL=https://api.example.com npm run build`).
   * When unset, the client uses the relative path "/api", which works in
   * both the Vite dev server (proxied) and single-origin production
   * deployments. Never point this at an untrusted origin.
   */
  readonly VITE_API_BASE_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
