/**
 * history.store — 单元测试
 *
 * 测试: 状态初始化、过滤、分页、选择管理
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useHistoryStore } from '@/stores/history.store'
import type { HistoryRecord } from '@/types/api'

function makeRecord(overrides: Partial<HistoryRecord> = {}): HistoryRecord {
  return {
    id: 1,
    filename: 'test.mp3',
    mode: 'quick',
    total_score: 80,
    level: '优秀',
    grade: 'A',
    created_at: '2026-07-21 10:00:00',
    duration: 180,
    ...overrides,
  }
}

describe('useHistoryStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('初始状态: records 为空数组', () => {
    const store = useHistoryStore()
    expect(store.records).toEqual([])
  })

  it('初始状态: filter 为 all', () => {
    const store = useHistoryStore()
    expect(store.filter).toBe('all')
  })

  it('初始状态: loading 为 false', () => {
    const store = useHistoryStore()
    expect(store.loading).toBe(false)
  })

  it('初始状态: selectedIds 为空', () => {
    const store = useHistoryStore()
    expect(store.selectedIds).toEqual([])
  })

  it('setFilter 修改筛选并重置页码', () => {
    const store = useHistoryStore()
    store.currentPage = 3
    store.setFilter('today')
    expect(store.filter).toBe('today')
    expect(store.currentPage).toBe(1)
  })

  it('setSearch 过滤记录', () => {
    const store = useHistoryStore()
    store.records = [
      makeRecord({ id: 1, filename: 'hello.mp3' }),
      makeRecord({ id: 2, filename: 'world.mp3' }),
    ]
    store.setSearch('hello')
    expect(store.filteredRecords).toHaveLength(1)
    expect(store.filteredRecords[0].id).toBe(1)
  })

  it('toggleSelect 切换选中状态', () => {
    const store = useHistoryStore()
    store.records = [
      makeRecord({ id: 1 }),
      makeRecord({ id: 2 }),
    ]
    store.currentPage = 1

    store.toggleSelect(1)
    expect(store.selectedIds).toEqual([1])

    store.toggleSelect(2)
    expect(store.selectedIds).toEqual([1, 2])

    store.toggleSelect(1)
    expect(store.selectedIds).toEqual([2])
  })

  it('toggleSelectAll 全选/取消全选', () => {
    const store = useHistoryStore()
    store.records = [
      makeRecord({ id: 1 }),
      makeRecord({ id: 2 }),
      makeRecord({ id: 3 }),
    ]

    store.toggleSelectAll()
    expect(store.selectedIds).toEqual([1, 2, 3])

    store.toggleSelectAll()
    expect(store.selectedIds).toEqual([])
  })

  it('hasSelection 计算属性', () => {
    const store = useHistoryStore()
    expect(store.hasSelection).toBe(false)

    store.selectedIds = [1]
    expect(store.hasSelection).toBe(true)
  })

  it('goToPage 分页导航', () => {
    const store = useHistoryStore()
    store.records = Array.from({ length: 50 }, (_, i) =>
      makeRecord({ id: i + 1, filename: `song_${i + 1}.mp3` }),
    )

    expect(store.currentPage).toBe(1)
    store.goToPage(2)
    expect(store.currentPage).toBe(2)
    store.goToPage(0) // below minimum
    expect(store.currentPage).toBe(1)
  })

  it('paginatedRecords 分页数据', () => {
    const store = useHistoryStore()
    store.records = Array.from({ length: 50 }, (_, i) =>
      makeRecord({ id: i + 1, filename: `song_${i + 1}.mp3` }),
    )
    store.pageSize = 20

    expect(store.paginatedRecords).toHaveLength(20)
    expect(store.paginatedRecords[0].id).toBe(1)

    store.goToPage(3)
    expect(store.paginatedRecords).toHaveLength(10) // 50 total, 20 per page, page 3 = 10
  })

  it('totalPages 计算属性', () => {
    const store = useHistoryStore()
    store.records = Array.from({ length: 50 }, (_, i) =>
      makeRecord({ id: i + 1 }),
    )
    expect(store.totalPages).toBe(3)

    store.records = []
    // Math.max(1, ...) 确保空列表至少显示第 1 页 (而非第 0 页)
    expect(store.totalPages).toBe(1)
  })
})
