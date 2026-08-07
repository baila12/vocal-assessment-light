/**
 * songs.store 音准增强 — 单元测试
 *
 * v7.13: fetchSongPitch (参考音高缓存) + compareWithSong (选歌对比)。
 * mock @/api/client (对齐 scoring.test.ts 模式)。
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSongsStore } from '@/stores/songs.store'

vi.mock('@/api/client', () => ({
  apiClient: {
    get: vi.fn(),
    upload: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    constructor(public status: number, message: string, public detail?: unknown) {
      super(message)
      this.name = 'ApiError'
    }
  },
}))

import { apiClient } from '@/api/client'

const mockedGet = apiClient.get as ReturnType<typeof vi.fn>
const mockedUpload = apiClient.upload as ReturnType<typeof vi.fn>

describe('useSongsStore — pitch', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedGet.mockReset()
    mockedUpload.mockReset()
  })

  it('fetchSongPitch: 成功 → 返回 PitchPoint[]', async () => {
    mockedGet.mockResolvedValue({
      success: true,
      data: {
        song_id: 'abc',
        frequencies: [440, 440, 0],
        times: [0, 0.032, 0.064],
        confidence: [1, 0.9, 0.1],
        sample_rate: 16000,
        hop_length: 512,
        duration_seconds: 0.064,
        frame_count: 3,
      },
    })
    const store = useSongsStore()
    const points = await store.fetchSongPitch('abc')

    expect(mockedGet).toHaveBeenCalledWith('/api/v1/songs/abc/pitch')
    expect(points).toHaveLength(3)
    expect(points[0]).toEqual({ time: 0, frequency: 440, confidence: 1 })
    expect(points[2]).toEqual({ time: 0.064, frequency: 0, confidence: 0.1 })
  })

  it('fetchSongPitch: 缓存命中 → 不重复请求', async () => {
    mockedGet.mockResolvedValue({
      success: true,
      data: {
        song_id: 'abc',
        frequencies: [440],
        times: [0],
        confidence: [1],
        sample_rate: 16000,
        hop_length: 512,
        duration_seconds: 0,
        frame_count: 1,
      },
    })
    const store = useSongsStore()
    await store.fetchSongPitch('abc')
    await store.fetchSongPitch('abc')

    expect(mockedGet).toHaveBeenCalledTimes(1)
  })

  it('fetchSongPitch: 响应失败 → 返回空数组', async () => {
    mockedGet.mockResolvedValue({ success: false, data: null })
    const store = useSongsStore()
    const points = await store.fetchSongPitch('abc')
    expect(points).toEqual([])
  })

  it('fetchSongPitch: 请求异常 → 返回空数组且不抛出', async () => {
    mockedGet.mockRejectedValue(new Error('network'))
    const store = useSongsStore()
    const points = await store.fetchSongPitch('abc')
    expect(points).toEqual([])
  })

  it('compareWithSong: 上传成功 → 返回对比数据', async () => {
    mockedUpload.mockResolvedValue({
      success: true,
      data: {
        score: 85,
        level: '良好',
        confidence: 0.9,
        pitch_match_rate: 88.5,
        rhythm_match_rate: 82.3,
        avg_cents_error: 15.2,
        diagnosis: ['音准良好'],
        suggestions: [],
        method: 'three_level_dtw',
      },
    })
    const store = useSongsStore()
    const formData = new FormData()
    formData.append('user_file', new Blob(['x']), 'user.wav')

    const data = await store.compareWithSong('abc', formData)

    expect(mockedUpload).toHaveBeenCalledWith(
      '/api/v1/songs/abc/compare',
      formData,
    )
    expect(data.score).toBe(85)
    expect(data.pitch_match_rate).toBe(88.5)
  })

  it('compareWithSong: 失败 → 抛出错误', async () => {
    mockedUpload.mockResolvedValue({ success: false, error: '对比失败' })
    const store = useSongsStore()
    await expect(store.compareWithSong('abc', new FormData())).rejects.toThrow()
  })
})
