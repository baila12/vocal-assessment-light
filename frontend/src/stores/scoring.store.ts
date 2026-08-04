/**
 * 评分权重配置 Store — v7.11 (scoring-config.feature)
 *
 * 管理:
 * - 风格预设 (GET /api/v1/scoring/presets): 流行/美声/民族/说唱
 * - 当前选中权重 (预设 or 自定义滑块)
 * - 权重合法性 (总和=100%, 单维 ≤50%)
 * - 纯前端重算 (POST /api/v1/scoring/apply-weights)
 */
import { ref, computed } from 'vue'
import { defineStore } from 'pinia'
import { apiClient, ApiError } from '@/api/client'
import type {
  ScoringPresetsData,
  ScoringPresetsResponse,
  ScoringWeightsDto,
  ApplyWeightsRequest,
  ApplyWeightsResponse,
  ApplyWeightsData,
} from '@/types/api'

export const DIMENSION_KEYS = ['pitch', 'rhythm', 'breath', 'technique', 'muscle', 'artistry'] as const

const WEIGHTS_EPSILON = 1e-6

export const useScoringStore = defineStore('scoring', () => {
  const presetsData = ref<ScoringPresetsData | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  /** 当前选中预设名; 'custom' = 自定义滑块; 'default' = 默认权重 */
  const selectedPreset = ref<string>('default')

  /** 自定义权重 (小数, 各维 0-0.5) — 滑块模式编辑对象 */
  const customWeights = ref<ScoringWeightsDto>({
    pitch: 0.2, rhythm: 0.16, breath: 0.16,
    technique: 0.2, muscle: 0.12, artistry: 0.16,
  })

  const isLoaded = computed(() => presetsData.value !== null)

  /** 全部可选预设 (含 默认 + 4 风格) */
  const allPresets = computed(() => {
    const d = presetsData.value
    if (!d) return []
    return [d.default, ...d.presets]
  })

  /** 当前生效权重 — 预设/默认/自定义 */
  const activeWeights = computed<ScoringWeightsDto>(() => {
    const d = presetsData.value
    if (selectedPreset.value === 'custom') return { ...customWeights.value }
    if (selectedPreset.value === 'default') return d ? { ...d.default.weights } : defaultWeights()
    const found = d?.presets.find((p) => p.name === selectedPreset.value)
    return found ? { ...found.weights } : defaultWeights()
  })

  const activePresetLabel = computed(() => {
    if (selectedPreset.value === 'custom') return '自定义'
    if (selectedPreset.value === 'default') return '默认 (v7.4)'
    return presetsData.value?.presets.find((p) => p.name === selectedPreset.value)?.label ?? '默认 (v7.4)'
  })

  /** 权重总和 (0-1) */
  const weightSum = computed(() => {
    const w = activeWeights.value
    return DIMENSION_KEYS.reduce((acc, k) => acc + w[k], 0)
  })

  /** 是否合法: 总和=100% 且 各维 ≤50% */
  const isValid = computed(() => {
    const w = activeWeights.value
    if (Math.abs(weightSum.value - 1) > WEIGHTS_EPSILON) return false
    return DIMENSION_KEYS.every((k) => w[k] >= 0 && w[k] <= 0.5)
  })

  /** 自动归一化: 按比例缩放到总和=100%, 保留相对权重 */
  function autoNormalize(): void {
    const w = { ...customWeights.value }
    const s = DIMENSION_KEYS.reduce((acc, k) => acc + w[k], 0)
    if (s <= 0) return
    DIMENSION_KEYS.forEach((k) => {
      w[k] = round4(w[k] / s)
    })
    customWeights.value = w
  }

  async function fetchPresets(): Promise<void> {
    if (loading.value) return
    loading.value = true
    error.value = null
    try {
      const json = await apiClient.get<ScoringPresetsResponse>('/api/v1/scoring/presets')
      if (json.success && json.data) {
        presetsData.value = json.data
      } else {
        error.value = '获取权重预设失败'
      }
    } catch (e: unknown) {
      error.value = e instanceof ApiError ? e.message : '网络错误'
    } finally {
      loading.value = false
    }
  }

  /**
   * 纯前端重算 — 用当前选中权重对既有维度分数重新计算总分.
   * dimensionScores: 六维分数; timbreAdjustment: 复用原分析音色调整.
   */
  async function recalc(
    dimensionScores: Record<string, number>,
    timbreAdjustment = 0,
  ): Promise<ApplyWeightsData | null> {
    if (!isValid.value) return null
    const body: ApplyWeightsRequest = {
      dimension_scores: dimensionScores,
      timbre_adjustment: timbreAdjustment,
    }
    if (selectedPreset.value === 'custom') {
      body.weights = { ...customWeights.value }
    } else if (selectedPreset.value !== 'default') {
      body.preset = selectedPreset.value
    }
    try {
      const json = await apiClient.post<ApplyWeightsResponse>('/api/v1/scoring/apply-weights', body)
      return json.success && json.data ? json.data : null
    } catch (e: unknown) {
      error.value = e instanceof ApiError ? e.message : '网络错误'
      return null
    }
  }

  return {
    presetsData,
    loading,
    error,
    selectedPreset,
    customWeights,
    isLoaded,
    allPresets,
    activeWeights,
    activePresetLabel,
    weightSum,
    isValid,
    fetchPresets,
    autoNormalize,
    recalc,
  }
})

function defaultWeights(): ScoringWeightsDto {
  return { pitch: 0.13, rhythm: 0.12, breath: 0.22, technique: 0.25, muscle: 0.15, artistry: 0.13 }
}

function round4(n: number): number {
  return Math.round(n * 10000) / 10000
}
