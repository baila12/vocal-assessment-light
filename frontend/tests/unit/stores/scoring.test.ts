/**
 * scoring.store — 单元测试
 *
 * 测试: 权重合法性、预设加载、自定义权重、自动归一化、纯前端重算
 * v7.11: 评分权重可配置 (scoring-config.feature)
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useScoringStore } from '@/stores/scoring.store'
import type { ScoringPresetsData } from '@/types/api'

// ── mock apiClient ──
vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
  },
  ApiError: class ApiError extends Error {},
}))

import { apiClient } from '@/api/client'

const mockedGet = apiClient.get as unknown as ReturnType<typeof vi.fn>
const mockedPost = apiClient.post as unknown as ReturnType<typeof vi.fn>

function makePresetsData(): ScoringPresetsData {
  return {
    default: { name: 'default', label: '默认 (v7.4)', weights: { pitch: 0.13, rhythm: 0.12, breath: 0.22, technique: 0.25, muscle: 0.15, artistry: 0.13 } },
    presets: [
      { name: 'pop', label: '流行', weights: { pitch: 0.21, rhythm: 0.17, breath: 0.13, technique: 0.17, muscle: 0.15, artistry: 0.17 } },
      { name: 'rap', label: '说唱', weights: { pitch: 0.08, rhythm: 0.30, breath: 0.09, technique: 0.13, muscle: 0.15, artistry: 0.25 } },
    ],
    default_preset: 'pop',
  }
}

describe('useScoringStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedGet.mockReset()
    mockedPost.mockReset()
  })

  it('初始状态: 默认选中 default', () => {
    const store = useScoringStore()
    expect(store.selectedPreset).toBe('default')
    expect(store.presetsData).toBeNull()
  })

  it('fetchPresets 加载预设数据', async () => {
    mockedGet.mockResolvedValue({ success: true, data: makePresetsData() })
    const store = useScoringStore()
    await store.fetchPresets()
    expect(store.isLoaded).toBe(true)
    expect(store.allPresets.length).toBe(3) // default + pop + rap
  })

  it('默认权重总和 = 100% 且合法', async () => {
    mockedGet.mockResolvedValue({ success: true, data: makePresetsData() })
    const store = useScoringStore()
    await store.fetchPresets()
    expect(store.weightSum).toBeCloseTo(1.0)
    expect(store.isValid).toBe(true)
  })

  it('选中 rap 预设时应用其权重', async () => {
    mockedGet.mockResolvedValue({ success: true, data: makePresetsData() })
    const store = useScoringStore()
    await store.fetchPresets()
    store.selectedPreset = 'rap'
    expect(store.activeWeights.rhythm).toBe(0.30)
    expect(store.weightSum).toBeCloseTo(1.0)
    expect(store.activePresetLabel).toBe('说唱')
  })

  it('自定义模式使用滑块权重', async () => {
    const store = useScoringStore()
    store.selectedPreset = 'custom'
    store.customWeights = { pitch: 0.3, rhythm: 0.2, breath: 0.15, technique: 0.15, muscle: 0.1, artistry: 0.1 }
    expect(store.weightSum).toBeCloseTo(1.0)
    expect(store.isValid).toBe(true)
  })

  it('非法自定义权重: 总和 ≠ 100% 时 isValid 为 false', async () => {
    const store = useScoringStore()
    store.selectedPreset = 'custom'
    store.customWeights = { pitch: 0.3, rhythm: 0.3, breath: 0.25, technique: 0.2, muscle: 0.1, artistry: 0.0 }
    expect(store.weightSum).toBeCloseTo(1.15)
    expect(store.isValid).toBe(false)
  })

  it('非法自定义权重: 单维 > 50% 时 isValid 为 false', async () => {
    const store = useScoringStore()
    store.selectedPreset = 'custom'
    store.customWeights = { pitch: 0.55, rhythm: 0.1, breath: 0.1, technique: 0.1, muscle: 0.1, artistry: 0.05 }
    expect(store.isValid).toBe(false)
  })

  it('autoNormalize 按比例缩放到 100% 且保留相对权重', async () => {
    const store = useScoringStore()
    store.selectedPreset = 'custom'
    // 总和 150% → 归一化后总和 100%
    store.customWeights = { pitch: 0.45, rhythm: 0.3, breath: 0.3, technique: 0.15, muscle: 0.15, artistry: 0.15 }
    store.autoNormalize()
    expect(store.weightSum).toBeCloseTo(1.0, 4)
    // 相对比例保持: 45:30 = 0.5:0.333... (保留 ratio)
    const w = store.customWeights
    expect(w.pitch / w.rhythm).toBeCloseTo(1.5)
    expect(store.isValid).toBe(true)
  })

  it('recalc 传自定义权重时调用 apply-weights API', async () => {
    mockedPost.mockResolvedValue({
      success: true,
      data: { total_score: 78, level: '优秀', grade: 'A', color: '#3b82f6', stars: '★★', weighted_dimensions: {}, applied_weights: {}, applied_preset: 'custom' },
    })
    const store = useScoringStore()
    store.selectedPreset = 'custom'
    const result = await store.recalc(
      { pitch: 90, rhythm: 50, breath: 70, technique: 70, muscle: 70, artistry: 70 },
      0,
    )
    expect(result?.total_score).toBe(78)
    const body = mockedPost.mock.calls[0][1]
    expect(body.weights).toBeDefined()
    expect(body.preset).toBeUndefined()
  })

  it('recalc 传预设名时使用 preset', async () => {
    mockedPost.mockResolvedValue({
      success: true,
      data: { total_score: 65, level: '良好', grade: 'B', color: '#10b981', stars: '★★', weighted_dimensions: {}, applied_weights: {}, applied_preset: 'rap' },
    })
    const store = useScoringStore()
    store.selectedPreset = 'rap'
    const result = await store.recalc(
      { pitch: 90, rhythm: 50, breath: 70, technique: 70, muscle: 70, artistry: 70 },
      0,
    )
    expect(result?.total_score).toBe(65)
    const body = mockedPost.mock.calls[0][1]
    expect(body.preset).toBe('rap')
  })

  it('recalc 在权重非法时不请求 API', async () => {
    const store = useScoringStore()
    store.selectedPreset = 'custom'
    store.customWeights = { pitch: 0.3, rhythm: 0.3, breath: 0.25, technique: 0.2, muscle: 0.1, artistry: 0.0 }
    const result = await store.recalc({ pitch: 80, rhythm: 80, breath: 80, technique: 80, muscle: 80, artistry: 80 })
    expect(result).toBeNull()
    expect(mockedPost).not.toHaveBeenCalled()
  })
})
