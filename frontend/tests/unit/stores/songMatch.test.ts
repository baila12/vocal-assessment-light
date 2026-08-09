/**
 * songMatch.store — 单元测试
 *
 * v7.14: 上传音频自动匹配标准歌曲。
 * mock @/api/client (对齐 songsPitch.test.ts 模式)。
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSongMatchStore } from '@/stores/songMatch.store'
import type { MatchCandidate, SongCompareData } from '@/types/api'

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

function makeFile(name = 'user.wav'): File {
  return new File(['fake-wav'], name, { type: 'audio/wav' })
}

function makeCandidate(overrides: Partial<MatchCandidate> = {}): MatchCandidate {
  return {
    song_id: 'abc',
    title: '月亮代表我的心',
    artist: '邓丽君',
    confidence: 0.93,
    factors: { bpm: 0.9, chroma: 0.95, key: 1.0, duration: 0.87 },
    bpm_diff: 2.0,
    key_diff_semitones: 0,
    detected_key: 'C',
    ...overrides,
  }
}

describe('useSongMatchStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockedGet.mockReset()
    mockedUpload.mockReset()
  })

  it('初始状态: 未匹配, 无候选, 未选中', () => {
    const store = useSongMatchStore()
    expect(store.isMatching).toBe(false)
    expect(store.candidates).toEqual([])
    expect(store.matchedSong).toBeNull()
    expect(store.fallbackReason).toBe('')
    expect(store.selectedSongId).toBeNull()
    expect(store.compareResult).toBeNull()
  })

  it('matchAudio: 命中 → 记录最佳匹配并自动选中', async () => {
    mockedUpload.mockResolvedValue({
      success: true,
      matched: true,
      matched_song: { id: 'abc', title: '月亮代表我的心', artist: '邓丽君', confidence: 0.93 },
      candidates: [makeCandidate()],
      fallback_reason: '',
      detected_key: 'C',
      partial: false,
      elapsed_ms: 120,
      error: null,
    })
    const store = useSongMatchStore()
    await store.matchAudio(makeFile())

    expect(mockedUpload).toHaveBeenCalledWith('/api/v1/songs/match', expect.any(FormData))
    expect(store.isMatching).toBe(false)
    expect(store.matchedSong?.id).toBe('abc')
    expect(store.candidates).toHaveLength(1)
    expect(store.selectedSongId).toBe('abc')
    expect(store.fallbackReason).toBe('')
    expect(store.error).toBeNull()
  })

  it('matchAudio: 无匹配 → matchedSong 为 null, fallback 保留', async () => {
    mockedUpload.mockResolvedValue({
      success: true,
      matched: false,
      matched_song: null,
      candidates: [makeCandidate({ confidence: 0.4 })],
      fallback_reason: 'no_match',
      detected_key: 'A',
      partial: false,
      elapsed_ms: 80,
      error: null,
    })
    const store = useSongMatchStore()
    await store.matchAudio(makeFile())

    expect(store.matchedSong).toBeNull()
    expect(store.selectedSongId).toBeNull()
    expect(store.fallbackReason).toBe('no_match')
    expect(store.candidates).toHaveLength(1)
  })

  it('matchAudio: 请求失败 → error 记录, 不抛出', async () => {
    mockedUpload.mockRejectedValue(new Error('network'))
    const store = useSongMatchStore()
    await expect(store.matchAudio(makeFile())).resolves.toBeUndefined()
    expect(store.error).toBe('network')
    expect(store.isMatching).toBe(false)
  })

  it('selectCandidate: 切换选中的歌曲', () => {
    const store = useSongMatchStore()
    store.candidates = [makeCandidate({ song_id: 'a' }), makeCandidate({ song_id: 'b' })]
    store.selectCandidate('b')
    expect(store.selectedSongId).toBe('b')
    store.selectCandidate(null)
    expect(store.selectedSongId).toBeNull()
  })

  it('clearMatch: 重置匹配结果与对比结果', async () => {
    mockedUpload.mockResolvedValue({ success: true })
    const store = useSongMatchStore()
    store.candidates = [makeCandidate()]
    store.matchedSong = { id: 'abc', title: '月亮', artist: '邓丽君', confidence: 0.9 }
    store.compareResult = { score: 85 } as SongCompareData
    store.clearMatch()
    expect(store.candidates).toEqual([])
    expect(store.matchedSong).toBeNull()
    expect(store.selectedSongId).toBeNull()
    expect(store.compareResult).toBeNull()
  })

  it('compareWithSelected: 未选中歌曲 → 抛出错误', async () => {
    const store = useSongMatchStore()
    await expect(store.compareWithSelected(makeFile())).rejects.toThrow('请先选择匹配的歌曲')
    expect(mockedUpload).not.toHaveBeenCalled()
  })

  it('compareWithSelected: 成功 → 调选歌对比端点并返回数据', async () => {
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
    const store = useSongMatchStore()
    store.selectedSongId = 'abc'
    const file = makeFile()
    const data = await store.compareWithSelected(file)

    expect(mockedUpload).toHaveBeenCalledWith(
      '/api/v1/songs/abc/compare',
      expect.any(FormData),
    )
    expect(data.score).toBe(85)
    expect(store.compareResult?.pitch_match_rate).toBe(88.5)
    expect(store.isComparing).toBe(false)
  })

  it('compareWithSelected: 失败 → 抛出错误', async () => {
    mockedUpload.mockRejectedValue(new Error('对比失败'))
    const store = useSongMatchStore()
    store.selectedSongId = 'abc'
    await expect(store.compareWithSelected(makeFile())).rejects.toThrow('对比失败')
    expect(store.isComparing).toBe(false)
  })

  it('fetchUserPitch: 成功 → 映射为 PitchPoint[]', async () => {
    mockedUpload.mockResolvedValue({
      success: true,
      data: {
        duration: 0.064,
        sample_rate: 16000,
        hop_length: 512,
        frequencies: [440, 440, 0],
        times: [0, 0.032, 0.064],
        confidence: [1, 0.9, 0.1],
        frame_count: 3,
      },
      error: null,
    })
    const store = useSongMatchStore()
    const points = await store.fetchUserPitch(makeFile())

    expect(mockedUpload).toHaveBeenCalledWith('/api/v1/extract-pitch', expect.any(FormData))
    expect(points).toHaveLength(3)
    expect(points[0]).toEqual({ time: 0, frequency: 440, confidence: 1 })
    expect(points[2]).toEqual({ time: 0.064, frequency: 0, confidence: 0.1 })
  })

  it('fetchUserPitch: 失败 → 返回空数组不抛出', async () => {
    mockedUpload.mockResolvedValue({ success: false, error: '音高提取失败' })
    const store = useSongMatchStore()
    const points = await store.fetchUserPitch(makeFile())
    expect(points).toEqual([])
  })
})
