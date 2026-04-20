/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
  readonly VITE_DEFAULT_API_KEY?: string
  readonly VITE_ENABLE_DEV_CONTROLS?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
