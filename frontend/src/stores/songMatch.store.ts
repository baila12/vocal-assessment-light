/**
 * 上传音频自动匹配标准歌曲 — Pinia store
 *
 * v7.14: 上传用户录音 → POST /api/v1/songs/match → 候选列表 → 选中歌曲
 *        → POST /api/v1/songs/{id}/compare (DTW 对比评分)
 *        → POST /api/v1/extract-pitch (用户录音音高曲线, 供 Phase 5 双轨叠加)
 * 无匹配时优雅回退绝对评分 (fallbackReason 透传后端原因)。
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { apiClient, ApiError } from '@/api/client'
import type {
  MatchedSong,
  MatchCandidate,
  MatchResultResponse,
  SongCompareData,
  SongCompareResponse,
  PitchExtractResponse,
} from '@/types/api'
import type { PitchPoint } from '@/types/pitch'

export const useSongMatchStore = defineStore('songMatch', () => {
  // ---- 状态 ----
  const isMatching = ref(false)
  const candidates = ref<MatchCandidate[]>([])
  const matchedSong = ref<MatchedSong | null>(null)
  const fallbackReason = ref('')
  const error = ref<string | null>(null)
  const selectedSongId = ref<string | null>(null)
  const isComparing = ref(false)
  const compareResult = ref<SongCompareData | null>(null)

  // ---- 操作 ----

  /** 上传用户录音并自动匹配 — 命中则自动选中最佳候选 */
  async function matchAudio(file: File, topN = 3): Promise<void> {
    isMatching.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('top_n', String(topN))

      const resp = await apiClient.upload<MatchResultResponse>('/api/v1/songs/match', formData)
      candidates.value = resp.candidates ?? []
      matchedSong.value = resp.matched ? resp.matched_song : null
      fallbackReason.value = resp.fallback_reason ?? ''
      // 命中最佳匹配时自动选中; 否则清空选中 (用户可手动挑候选)
      selectedSongId.value = resp.matched_song?.id ?? null
    } catch (e) {
      error.value = e instanceof ApiError || e instanceof Error ? e.message : '匹配失败'
      candidates.value = []
      matchedSong.value = null
      selectedSongId.value = null
    } finally {
      isMatching.value = false
    }
  }

  /** 手动切换选中的候选歌曲 */
  function selectCandidate(id: string | null): void {
    selectedSongId.value = id
  }

  /** 重置匹配结果与对比结果 (新上传/清除时调用) */
  function clearMatch(): void {
    candidates.value = []
    matchedSong.value = null
    fallbackReason.value = ''
    selectedSongId.value = null
    compareResult.value = null
  }

  /** 与选中的标准歌曲 DTW 对比 — 返回评分数据并写入 compareResult */
  async function compareWithSelected(userFile: File): Promise<SongCompareData> {
    const songId = selectedSongId.value
    if (!songId) {
      throw new Error('请先选择匹配的歌曲')
    }
    isComparing.value = true
    error.value = null
    try {
      const formData = new FormData()
      formData.append('user_file', userFile)

      const resp = await apiClient.upload<SongCompareResponse>(
        `/api/v1/songs/${songId}/compare`,
        formData,
      )
      if (!resp.success || !resp.data) {
        throw new Error(resp.error || '对比分析失败')
      }
      compareResult.value = resp.data
      return resp.data
    } catch (e) {
      error.value = e instanceof ApiError || e instanceof Error ? e.message : '对比分析失败'
      throw e
    } finally {
      isComparing.value = false
    }
  }

  /** 提取用户录音音高曲线 (POST /extract-pitch) — 供 Phase 5 双轨叠加用户轨 */
  async function fetchUserPitch(file: File): Promise<PitchPoint[]> {
    try {
      const formData = new FormData()
      formData.append('file', file)
      const resp = await apiClient.upload<PitchExtractResponse>('/api/v1/extract-pitch', formData)
      if (!resp.success || !resp.data) return []
      const data = resp.data
      return data.frequencies.map((f, i) => ({
        time: data.times[i] ?? 0,
        frequency: f,
        confidence: data.confidence[i] ?? 0,
      }))
    } catch (e) {
      error.value = e instanceof ApiError || e instanceof Error ? e.message : '音高提取失败'
      return []
    }
  }

  return {
    // 状态
    isMatching,
    candidates,
    matchedSong,
    fallbackReason,
    error,
    selectedSongId,
    isComparing,
    compareResult,
    // 操作
    matchAudio,
    selectCandidate,
    clearMatch,
    compareWithSelected,
    fetchUserPitch,
  }
})
