/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Core API base URL — set for public builds (default: http://localhost:9000). */
  readonly VITE_CORE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
