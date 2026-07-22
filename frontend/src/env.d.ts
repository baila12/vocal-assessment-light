/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}

interface Window {
  BACKEND_URL?: string
  /** Electron IPC bridge (undefined in browser/dev mode). */
  electronAPI?: {
    onBackendUrl: (callback: (url: string) => void) => void
    onBackendStatus: (callback: (status: string) => void) => void
    getBackendUrl: () => Promise<string>
  }
  __audioCleanup?: () => void
}
