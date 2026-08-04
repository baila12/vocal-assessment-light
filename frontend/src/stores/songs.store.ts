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
} from '@/types/api'

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
  }
})
