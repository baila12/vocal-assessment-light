/**
 * useApi — API 调用封装 composable
 *
 * 提供响应式 loading/error 状态 + 类型安全的方法
 * 零硬编码 URL — 使用 apiClient (window.BACKEND_URL 或 fallback)
 */

import { ref } from 'vue'
import { apiClient, ApiError } from '@/api/client'
import type { AssessmentResult, HistoryListResponse } from '@/types/api'

export function useApi() {
  const loading = ref(false)
  const error = ref<string | null>(null)

  function clearError(): void {
    error.value = null
  }

  async function request<T>(
    fn: () => Promise<T>,
    errorMessage = '请求失败',
  ): Promise<T> {
    loading.value = true
    error.value = null

    try {
      return await fn()
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : errorMessage
      error.value = msg
      throw e
    } finally {
      loading.value = false
    }
  }

  /** 上传音频并获取六维评分 */
  async function analyzeAudio(
    file: File,
    mode: 'quick' | 'professional' = 'quick',
  ): Promise<AssessmentResult> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('mode', mode)

    return request(async () => {
      const result = await apiClient.upload<{
        success: boolean
        data: AssessmentResult
      }>('/api/v1/upload', formData)

      if (!result.success) {
        throw new ApiError(500, '分析失败')
      }
      return result.data
    }, '音频分析失败')
  }

  /** 获取历史记录列表 */
  async function getHistory(
    filter: 'all' | 'today' | 'week' | 'month' = 'all',
  ): Promise<HistoryListResponse> {
    const dateParam = filter === 'all' ? '' : `?date=${filter}`
    return request(async () => {
      const result = await apiClient.get<{
        success: boolean
        data: HistoryListResponse
      }>(`/api/v1/history${dateParam}`)
      return result.data
    }, '加载历史记录失败')
  }

  /** 检查后端健康状态 */
  async function checkHealth(): Promise<{
    status: string
    version: string
    gpu: Record<string, unknown>
  }> {
    return request(async () => {
      return await apiClient.get('/health')
    }, '后端连接失败')
  }

  /** 删除历史记录 */
  async function deleteHistory(id: number): Promise<void> {
    return request(async () => {
      await apiClient.delete(`/api/v1/history/${id}`)
    }, '删除失败')
  }

  /** 获取音频文件 URL */
  function getAudioUrl(filepath: string): string {
    const base = apiClient.getBaseUrl()
    const encoded = encodeURIComponent(filepath)
    return `${base}/api/v1/audio?file=${encoded}`
  }

  return {
    loading,
    error,
    clearError,
    analyzeAudio,
    getHistory,
    checkHealth,
    deleteHistory,
    getAudioUrl,
  }
}
