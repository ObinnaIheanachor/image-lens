export const API_KEY_STORAGE = 'image_insight_api_key'
export const DEFAULT_API_KEY = import.meta.env.VITE_DEFAULT_API_KEY || ''
export const DEV_CONTROLS_ENABLED = (import.meta.env.VITE_ENABLE_DEV_CONTROLS || 'true') === 'true'

export function isDevMode(search: string): boolean {
  if (!DEV_CONTROLS_ENABLED) return false
  const params = new URLSearchParams(search)
  return params.get('mode') === 'dev'
}

export function resolveApiKey(): string {
  return sessionStorage.getItem(API_KEY_STORAGE) || DEFAULT_API_KEY
}

export function persistApiKey(apiKey: string): void {
  sessionStorage.setItem(API_KEY_STORAGE, apiKey)
}
