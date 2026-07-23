/**
 * useApi — 音频 URL 构建 composable
 *
 * v7.0.2: 移除未使用的方法 (analyzeAudio/getHistory/checkHealth/deleteHistory)。
 * Store 层直接使用 apiClient，此 composable 仅保留音频 URL 构建逻辑。
 * 零硬编码 URL — 使用 apiClient.getBaseUrl() (window.BACKEND_URL 或 fallback)
 */

import { apiClient } from '@/api/client'

export function useApi() {
  /** 获取音频文件 URL (零硬编码, 适配 Electron 动态端口) */
  function getAudioUrl(filepath: string): string {
    const base = apiClient.getBaseUrl()
    const encoded = encodeURIComponent(filepath)
    return `${base}/api/v1/audio?file=${encoded}`
  }

  return {
    getAudioUrl,
  }
}
