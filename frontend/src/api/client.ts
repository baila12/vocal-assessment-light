/**
 * HTTP 客户端 — 零硬编码 URL (ADR-3)
 *
 * Electron 模式: window.BACKEND_URL 由 preload 动态注入 (随机端口)
 * 开发模式 (Vite):  使用相对路径 → Vite 代理转发到后端
 * 生产/直接访问:    回退到 http://127.0.0.1:8000
 *
 * getBaseUrl() 每次调用时读取最新值，支持后端重启后 URL 变更。
 */

function getBaseUrl(): string {
  if (typeof window !== 'undefined') {
    // Electron: preload 注入动态端口
    const url = (window as unknown as Record<string, unknown>).BACKEND_URL as string | undefined
    if (url) return url
    // Electron API 存在但 URL 未就绪 → 等 preload 注入
    if ((window as unknown as Record<string, unknown>).electronAPI) return ''
  }
  // 开发模式 (Vite): 相对路径走 Vite 代理, 避免 CORS
  if (typeof import.meta !== 'undefined' && (import.meta as any).env?.DEV) {
    return ''
  }
  // 生产回退
  return 'http://127.0.0.1:8000'
}

/**
 * Check if running inside Electron.
 * Used by components to show dev-mode-only features conditionally.
 */
export function isElectron(): boolean {
  return typeof window !== 'undefined' && !!(window as unknown as Record<string, unknown>).electronAPI
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public detail?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `${getBaseUrl()}${path}`

  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, body.message || response.statusText, body)
  }

  return response.json()
}

export const apiClient = {
  get: <T>(path: string) => request<T>(path),

  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: 'POST',
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(path: string, body?: unknown) =>
    // 注意: DELETE 带 body 不符合 HTTP 规范, 但后端 /history/batch 需要 JSON body
    // Phase 6+ 计划迁移为 POST /history/batch-delete
    request<T>(path, {
      method: 'DELETE',
      body: body ? JSON.stringify(body) : undefined,
    }),


  upload: async <T>(path: string, formData: FormData): Promise<T> => {
    const url = `${getBaseUrl()}${path}`
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
    })

    if (!response.ok) {
      const body = await response.json().catch(() => ({}))
      throw new ApiError(response.status, body.message || response.statusText, body)
    }

    return response.json()
  },

  getBaseUrl,
}
