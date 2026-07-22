/**
 * 历史记录状态管理 — Pinia store
 *
 * 管理：分页列表、日期筛选、批量删除、搜索
 * v7.0 使用 FastAPI /api/v1/history 端点
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { apiClient, ApiError } from '@/api/client'
import type { HistoryRecord } from '@/types/api'

export type HistoryFilter = 'all' | 'today' | 'week' | 'month'

export const useHistoryStore = defineStore('history', () => {
  // ---- 状态 ----
  const records = ref<HistoryRecord[]>([])
  const filter = ref<HistoryFilter>('all')
  const loading = ref(false)
  const selectedIds = ref<number[]>([])
  const searchQuery = ref('')
  const currentPage = ref(1)
  const pageSize = ref(20)
  const total = ref(0)
  const error = ref<string | null>(null)

  // ---- 计算属性 ----
  const filteredRecords = computed(() => {
    let result = records.value
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      result = result.filter(
        (r) =>
          r.filename.toLowerCase().includes(q) ||
          r.level.includes(q) ||
          r.mode.includes(q),
      )
    }
    return result
  })

  const paginatedRecords = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    return filteredRecords.value.slice(start, start + pageSize.value)
  })

  const totalPages = computed(() =>
    Math.ceil(filteredRecords.value.length / pageSize.value),
  )

  const hasSelection = computed(() => selectedIds.value.length > 0)

  // ---- 操作 ----
  async function fetchHistory(): Promise<void> {
    loading.value = true
    error.value = null

    try {
      const dateParam = filter.value === 'all' ? '' : `?date=${filter.value}`
      const response = await apiClient.get<{
        success: boolean
        data: { records: HistoryRecord[]; total: number; page: number }
      }>(`/api/v1/history${dateParam}`)

      if (response.success && response.data) {
        records.value = response.data.records
        total.value = response.data.total
      } else {
        records.value = []
        total.value = 0
      }
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : '加载历史记录失败'
      records.value = []
    } finally {
      loading.value = false
    }
  }

  async function deleteRecord(id: number): Promise<void> {
    try {
      await apiClient.delete(`/api/v1/history/${id}`)
      records.value = records.value.filter((r) => r.id !== id)
      selectedIds.value = selectedIds.value.filter((sid) => sid !== id)
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : '删除失败'
      throw e
    }
  }

  async function deleteBatch(): Promise<void> {
    if (selectedIds.value.length === 0) return

    try {
      await apiClient.delete('/api/v1/history/batch', {
        ids: selectedIds.value,
      })
      records.value = records.value.filter(
        (r) => !selectedIds.value.includes(r.id),
      )
      selectedIds.value = []
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : '批量删除失败'
      throw e
    }
  }

  async function deleteAll(): Promise<void> {
    try {
      await apiClient.delete('/api/v1/history/all')
      records.value = []
      selectedIds.value = []
      total.value = 0
    } catch (e) {
      error.value = e instanceof ApiError ? e.message : '清空失败'
      throw e
    }
  }

  function setFilter(f: HistoryFilter): void {
    filter.value = f
    currentPage.value = 1
    fetchHistory()
  }

  function setSearch(q: string): void {
    searchQuery.value = q
    currentPage.value = 1
  }

  function toggleSelect(id: number): void {
    const idx = selectedIds.value.indexOf(id)
    if (idx === -1) {
      selectedIds.value.push(id)
    } else {
      selectedIds.value.splice(idx, 1)
    }
  }

  function toggleSelectAll(): void {
    if (selectedIds.value.length === paginatedRecords.value.length) {
      selectedIds.value = []
    } else {
      selectedIds.value = paginatedRecords.value.map((r) => r.id)
    }
  }

  function goToPage(page: number): void {
    currentPage.value = Math.max(1, Math.min(page, totalPages.value))
  }

  return {
    // 状态
    records,
    filter,
    loading,
    selectedIds,
    searchQuery,
    currentPage,
    pageSize,
    total,
    error,
    // 计算属性
    filteredRecords,
    paginatedRecords,
    totalPages,
    hasSelection,
    // 操作
    fetchHistory,
    deleteRecord,
    deleteBatch,
    deleteAll,
    setFilter,
    setSearch,
    toggleSelect,
    toggleSelectAll,
    goToPage,
  }
})
