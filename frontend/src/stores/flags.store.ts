/**
 * Feature Flags Store — v7.7
 *
 * 从 /api/v1/flags 获取算法状态、GPU、模型信息。
 * 用于 Settings 面板展示。v7.8: 使用 apiClient 统一错误处理。
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { apiClient, ApiError } from '@/api/client'

export interface FlagsGpu {
  available: boolean
  device: string | null
  name: string | null
  demucs_accelerated: boolean
}

export interface FlagsData {
  dimensions: Record<string, boolean>
  enhancements: Record<string, boolean>
  experimental: {
    audiofeat_installed: boolean
    timbral_models_installed: boolean
    fcpe: boolean
  }
  gpu: FlagsGpu
  models: Record<string, boolean>
  dimension_weights: Record<string, number>
}

/** Backend /api/v1/flags response shape */
interface FlagsResponse {
  success: boolean
  data: FlagsData
  error?: string
}

export const useFlagsStore = defineStore('flags', () => {
  const data = ref<FlagsData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isLoaded = computed(() => data.value !== null)

  const gpuLabel = computed(() => {
    if (!data.value?.gpu.available) return 'CPU'
    const d = data.value.gpu
    if (d.device === 'cuda') return `CUDA — ${d.name ?? 'GPU'}`
    if (d.device === 'mps') return 'Apple MPS'
    return d.device ?? '未知'
  })

  const enhancementTags = computed(() => {
    if (!data.value) return []
    const tags: { name: string; enabled: boolean }[] = []
    for (const [key, val] of Object.entries(data.value.enhancements)) {
      tags.push({ name: key, enabled: !!val })
    }
    return tags
  })

  async function fetchFlags(): Promise<void> {
    if (loading.value) return
    loading.value = true
    error.value = null
    try {
      const json = await apiClient.get<FlagsResponse>('/api/v1/flags')
      if (json.success && json.data) {
        data.value = json.data
      } else {
        error.value = '获取算法状态失败'
      }
    } catch (e: unknown) {
      error.value = e instanceof ApiError ? e.message : '网络错误'
    } finally {
      loading.value = false
    }
  }

  return {
    data,
    loading,
    error,
    isLoaded,
    gpuLabel,
    enhancementTags,
    fetchFlags,
  }
})
