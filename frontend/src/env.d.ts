/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface Window {
  BACKEND_URL?: string
  electronAPI?: {
    onBackendUrl: (callback: (url: string) => void) => void
  }
  __audioCleanup?: () => void
}
