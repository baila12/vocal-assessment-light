/**
 * Electron Preload — Phase 5
 *
 * ADR-1: 通过 contextBridge 暴露动态后端地址
 *
 * API:
 * - window.BACKEND_URL: 动态后端地址 (字符串, 初始为空)
 * - window.electronAPI.onBackendUrl(callback): 监听端口变更
 * - window.electronAPI.onBackendStatus(callback): 监听后端状态
 *
 * Security:
 * - contextIsolation: true — 渲染进程无法访问 Node.js
 * - 仅暴露明确的白名单 API
 */

import { contextBridge, ipcRenderer } from 'electron'

// ---- Shared state ----
// BACKEND_URL starts empty; set once backend is ready.
// In development (no Electron), window.BACKEND_URL is set by vite.config.ts
// or defaults to http://127.0.0.1:8000.

// ---- Exposed API ----
contextBridge.exposeInMainWorld('electronAPI', {
  /**
   * Listen for backend URL changes.
   * Fired once on startup, and again after auto-restart.
   */
  onBackendUrl: (callback: (url: string) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, url: string): void => {
      // Also update the global BACKEND_URL for direct access
      ;(window as unknown as Record<string, unknown>).BACKEND_URL = url
      callback(url)
    }
    ipcRenderer.on('set-backend-url', handler)
    // Return unsubscribe function
    return () => {
      ipcRenderer.removeListener('set-backend-url', handler)
    }
  },

  /**
   * Listen for backend status changes.
   * Values: 'starting' | 'restarting' | 'stopped'
   */
  onBackendStatus: (callback: (status: string) => void): (() => void) => {
    const handler = (_event: Electron.IpcRendererEvent, status: string): void => {
      callback(status)
    }
    ipcRenderer.on('backend-status', handler)
    return () => {
      ipcRenderer.removeListener('backend-status', handler)
    }
  },

  /**
   * Get current backend URL synchronously.
   * Returns empty string if backend not yet ready.
   */
  getBackendUrl: (): Promise<string> => {
    return ipcRenderer.invoke('get-backend-url')
  },
})
