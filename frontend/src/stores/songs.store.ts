/**
 * 标准歌曲库状态管理 — Pinia store
 *
 * 管理：分页列表、搜索、风格/难度筛选、上传、删除
 * v7.10 使用 FastAPI /api/v1/songs 端点 (服务端分页 + 服务端搜索/筛选)
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiClient, ApiError } from '@/api/client'
import type {
  SongRecord,
  SongCreateResponse,
  SongListResponse,
  SongDeleteResponse,
  SongPitchResponse,
  SongCompareData,
  SongCompareResponse,
} from '@/types/api'
import type { PitchPoint } from '@/types/pitch'

export const useSongsStore = defineStore('songs', () => {
  // ---- 状态 ----
  const songs = ref<SongRecord[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const currentPage = ref(1)
  const pageSize = ref(20)
  const total = ref(0)
  const searchQuery = ref('')
  const styleFilter = ref('')
  const difficultyFilter = ref('')
  const showUploadDialog = ref(false)
  const uploading = ref(false)
  /** v7.13: 歌曲参考音高缓存 (song_id → PitchPoint[], 选歌录音参考线) */
  const pitchCache = ref<Record<string, PitchPoint[]>>({})
  /** v7.14 审查 7.4 M7: 前端缓存上限 — 超出按 LRU 淘汰最久未访问的歌曲 */
  const PITCH_CACHE_MAX = 20
  let pitchCacheOrder: string[] = []

  function touchPitchOrder(id: string): void {
    pitchCacheOrder = pitchCacheOrder.filter((k) => k !== id)
    pitchCacheOrder.push(id)
  }

  // ---- 计算属性 ----
  // 后端不返回 total_pages, 前端计算 (至少 1 页)
  const totalPages = computed(() =>
    Math.max(1, Math.ceil(total.value / pageSize.value)),
  )

  const hasSongs = computed(() => songs.value.length > 0)

  const canUpload = computed(() => !uploading.value && !loading.value)

  // ---- 搜索防抖 ----
  let searchTimer: ReturnType<typeof setTimeout> | null = null

  // ---- 操作 ----
  async function fetchSongs(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const params = new URLSearchParams()
      params.set('page', String(currentPage.value))
      params.set('limit', String(pageSize.value))
      if (styleFilter.value) params.set('style', styleFilter.value)
      if (difficultyFilter.value) params.set('difficulty', difficultyFilter.value)
      if (searchQuery.value) params.set('search', searchQuery.value)

      // 后端 SongListResponse 扁平结构: { success, songs, total, page, limit }
      const response = await apiClient.get<SongListResponse>(
        `/api/v1/songs?${params.toString()}`,
      )

      if (response.success && response.songs) {
        songs.value = response.songs
        total.value = response.total
        currentPage.value = response.page
      } else {
        songs.value = []
        total.value = 0
      }
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : '加载歌曲列表失败'
      songs.value = []
    } finally {
      loading.value = false
    }
  }

  async function createSong(formData: FormData): Promise<SongRecord> {
    uploading.value = true
    error.value = null
    try {
      const response = await apiClient.upload<SongCreateResponse>(
        '/api/v1/songs',
        formData,
      )
      await fetchSongs()
      return response.song
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : '添加歌曲失败'
      throw e
    } finally {
      uploading.value = false
    }
  }

  async function deleteSong(id: string): Promise<void> {
    try {
      await apiClient.delete<SongDeleteResponse>(`/api/v1/songs/${id}`)
      removeSongLocally(id)
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : '删除歌曲失败'
      throw e
    }
  }

  function removeSongLocally(id: string): void {
    songs.value = songs.value.filter((s) => s.id !== id)
    total.value = Math.max(0, total.value - 1)
    // 审查 7.4 M8: 删除歌曲时同步清除前端音高缓存
    pitchCacheOrder = pitchCacheOrder.filter((k) => k !== id)
    if (pitchCache.value[id]) {
      const next = { ...pitchCache.value }
      delete next[id]
      pitchCache.value = next
    }
  }

  function goToPage(page: number): void {
    const target = Math.max(1, Math.min(page, totalPages.value))
    if (target !== currentPage.value) {
      currentPage.value = target
      fetchSongs()
    }
  }

  function setSearch(q: string): void {
    searchQuery.value = q
    currentPage.value = 1
    if (searchTimer) clearTimeout(searchTimer)
    searchTimer = setTimeout(() => {
      fetchSongs()
    }, 300)
  }

  function setStyleFilter(s: string): void {
    styleFilter.value = s
    currentPage.value = 1
    fetchSongs()
  }

  function setDifficultyFilter(d: string): void {
    difficultyFilter.value = d
    currentPage.value = 1
    fetchSongs()
  }

  function resetFilters(): void {
    searchQuery.value = ''
    styleFilter.value = ''
    difficultyFilter.value = ''
    currentPage.value = 1
    if (searchTimer) clearTimeout(searchTimer)
    fetchSongs()
  }

  function openUploadDialog(): void {
    showUploadDialog.value = true
  }

  function closeUploadDialog(): void {
    showUploadDialog.value = false
  }

  // ---- v7.13: 选歌录音参考音高 + 选歌对比 ----

  async function fetchSongPitch(id: string): Promise<PitchPoint[]> {
    if (pitchCache.value[id]) {
      touchPitchOrder(id) // 刷新为最近访问
      return pitchCache.value[id]
    }
    try {
      const resp = await apiClient.get<SongPitchResponse>(`/api/v1/songs/${id}/pitch`)
      if (!resp.success || !resp.data) return []
      const data = resp.data
      const points: PitchPoint[] = data.frequencies.map((f, i) => ({
        time: data.times[i] ?? 0,
        frequency: f,
        confidence: data.confidence[i] ?? 0,
      }))
      // 写缓存 + LRU 上限 (审查 7.4 M7: 防长期使用内存无界增长)
      touchPitchOrder(id)
      const next = { ...pitchCache.value, [id]: points }
      while (pitchCacheOrder.length > PITCH_CACHE_MAX) {
        const oldest = pitchCacheOrder.shift()
        if (oldest !== undefined) delete next[oldest]
      }
      pitchCache.value = next
      return points
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : '加载参考音高失败'
      return []
    }
  }

  async function compareWithSong(id: string, formData: FormData): Promise<SongCompareData> {
    try {
      const resp = await apiClient.upload<SongCompareResponse>(
        `/api/v1/songs/${id}/compare`,
        formData,
      )
      if (!resp.success || !resp.data) {
        throw new Error(resp.error || '对比分析失败')
      }
      return resp.data
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : '对比分析失败'
      throw e
    }
  }

  return {
    // 状态
    songs,
    loading,
    error,
    currentPage,
    pageSize,
    total,
    searchQuery,
    styleFilter,
    difficultyFilter,
    showUploadDialog,
    uploading,
    // 计算属性
    totalPages,
    hasSongs,
    canUpload,
    // 操作
    fetchSongs,
    createSong,
    deleteSong,
    removeSongLocally,
    goToPage,
    setSearch,
    setStyleFilter,
    setDifficultyFilter,
    resetFilters,
    openUploadDialog,
    closeUploadDialog,
    // v7.13
    pitchCache,
    fetchSongPitch,
    compareWithSong,
  }
})
