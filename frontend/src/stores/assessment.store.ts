/**
 * 评估状态管理 — Pinia store
 *
 * 管理：上传分析、进度追踪、WebSocket 流式评分、当前结果
 * v7.0 六维评分：pitch, rhythm, breath, technique, muscle_strength, artistry + timbre_adjustment
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiClient, ApiError } from '@/api/client'
import type { AssessmentResult } from '@/types/api'

export interface AnalysisProgress {
  stage: string
  percent: number
  message: string
}

export interface PartialScore {
  pitch?: number
  rhythm?: number
  progress: number
}

export const useAssessmentStore = defineStore('assessment', () => {
  // ---- 状态 ----
  const isAnalyzing = ref(false)
  const progress = ref<AnalysisProgress>({ stage: '', percent: 0, message: '' })
  const currentResult = ref<AssessmentResult | null>(null)
  const currentMode = ref<'quick' | 'professional'>('quick')
  const streamingScores = ref<PartialScore[]>([])
  const error = ref<string | null>(null)

  // ---- 计算属性 ----
  const totalScore = computed(() => currentResult.value?.total_score ?? 0)
  const level = computed(() => currentResult.value?.level ?? '')
  const grade = computed(() => currentResult.value?.grade ?? '')
  const heuristicDimensions = computed(() =>
    currentResult.value?.heuristic_dimensions ?? [],
  )
  const isVoice = computed(() => currentResult.value?.is_voice ?? true)
  const scores = computed(() => currentResult.value?.scores ?? null)
  const timbreAdjustment = computed(() => currentResult.value?.timbre_adjustment ?? 0)
  const advice = computed(() => currentResult.value?.advice ?? [])

  // ---- 操作 ----
  function setMode(mode: 'quick' | 'professional'): void {
    currentMode.value = mode
  }

  function resetProgress(): void {
    progress.value = { stage: '', percent: 0, message: '' }
    error.value = null
  }

  async function uploadAndAnalyze(file: File, mode: string): Promise<AssessmentResult> {
    isAnalyzing.value = true
    resetProgress()
    streamingScores.value = []

    progress.value = { stage: 'upload', percent: 5, message: '正在上传音频...' }

    const formData = new FormData()
    formData.append('file', file)
    formData.append('mode', mode)

    let progressTimer: ReturnType<typeof setInterval> | undefined

    try {
      progress.value = { stage: 'analyze', percent: 20, message: '正在分析音频特征...' }

      // 使用非精确进度指示 (后端为同步处理，Phase 5+ 改造为非阻塞 SSE)
      progressTimer = setInterval(() => {
        if (progress.value.percent < 85) {
          progress.value.percent += 8
          if (progress.value.percent > 85) progress.value.percent = 85
        }
      }, 1000)

      // 后端 UploadResponse 为扁平结构: { success, total_score, scores, level, ... }
      const result = await apiClient.upload<AssessmentResult & { success: boolean }>('/api/v1/upload', formData)

      if (!result.success) {
        throw new ApiError(500, '服务器返回异常数据')
      }

      progress.value = { stage: 'complete', percent: 100, message: '分析完成' }
      currentResult.value = result
      return result
    } catch (e) {
      const message = e instanceof ApiError ? e.message : '网络连接失败，请检查后端是否启动'
      error.value = message
      throw e
    } finally {
      if (progressTimer !== undefined) clearInterval(progressTimer)
      isAnalyzing.value = false
    }
  }

  function setResult(result: AssessmentResult): void {
    currentResult.value = result
  }

  function reset(): void {
    isAnalyzing.value = false
    progress.value = { stage: '', percent: 0, message: '' }
    currentResult.value = null
    streamingScores.value = []
    error.value = null
  }

  return {
    // 状态
    isAnalyzing,
    progress,
    currentResult,
    currentMode,
    streamingScores,
    error,
    // 计算属性
    totalScore,
    level,
    grade,
    heuristicDimensions,
    isVoice,
    scores,
    timbreAdjustment,
    advice,
    // 操作
    setMode,
    resetProgress,
    uploadAndAnalyze,
    setResult,
    reset,
  }
})
