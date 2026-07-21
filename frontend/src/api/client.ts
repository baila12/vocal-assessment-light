/**
 * HTTP 客户端 — 零硬编码 URL
 *
 * 后端 URL 由 Electron preload 注入 window.BACKEND_URL。
 * 开发模式 fallback: http://127.0.0.1:8000
 */

const BASE_URL = (typeof window !== 'undefined' && (window as any).BACKEND_URL)
  || 'http://127.0.0.1:8000'

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
  const url = `${BASE_URL}${path}`

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
    request<T>(path, {
      method: 'DELETE',
      body: body ? JSON.stringify(body) : undefined,
    }),

  upload: async <T>(path: string, formData: FormData): Promise<T> => {
    const url = `${BASE_URL}${path}`
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

  getBaseUrl: () => BASE_URL,
}
