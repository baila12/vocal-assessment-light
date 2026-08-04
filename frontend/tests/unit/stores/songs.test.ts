/**
 * songs.store — 单元测试
 *
 * 测试: 状态初始化、分页计算、筛选、上传对话框、本地删除
 * v7.10: 标准歌曲库前端
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSongsStore } from '@/stores/songs.store'
import type { SongRecord } from '@/types/api'

function makeSong(overrides: Partial<SongRecord> = {}): SongRecord {
  return {
    id: 'abc123def456',
    metadata: {
      title: '测试歌曲',
      artist: '测试歌手',
      key: 'C',
      bpm: 120,
      difficulty: 'beginner',
      style: 'pop',
    },
    filepath: '/data/songs/abc123def456.wav',
    duration_seconds: 180,
    feature_status: 'pending',
    scoring_config: {},
    created_at: '2026-08-04 10:00:00',
    ...overrides,
  }
}

describe('useSongsStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('初始状态: songs 为空数组', () => {
    const store = useSongsStore()
    expect(store.songs).toEqual([])
  })

  it('初始状态: loading 为 false', () => {
    const store = useSongsStore()
    expect(store.loading).toBe(false)
  })

  it('初始状态: error 为 null', () => {
    const store = useSongsStore()
    expect(store.error).toBeNull()
  })

  it('初始状态: currentPage 为 1', () => {
    const store = useSongsStore()
    expect(store.currentPage).toBe(1)
  })

  it('初始状态: pageSize 为 20', () => {
    const store = useSongsStore()
    expect(store.pageSize).toBe(20)
  })

  it('初始状态: styleFilter 为空字符串', () => {
    const store = useSongsStore()
    expect(store.styleFilter).toBe('')
  })

  it('初始状态: difficultyFilter 为空字符串', () => {
    const store = useSongsStore()
    expect(store.difficultyFilter).toBe('')
  })

  it('初始状态: 上传对话框关闭', () => {
    const store = useSongsStore()
    expect(store.showUploadDialog).toBe(false)
  })

  it('totalPages: 空列表时为 1', () => {
    const store = useSongsStore()
    store.total = 0
    expect(store.totalPages).toBe(1)
  })

  it('totalPages: 计算分页数', () => {
    const store = useSongsStore()
    store.total = 45
    store.pageSize = 20
    expect(store.totalPages).toBe(3)
  })

  it('totalPages: 整页边界', () => {
    const store = useSongsStore()
    store.total = 40
    store.pageSize = 20
    expect(store.totalPages).toBe(2)
  })

  it('hasSongs: 空列表返回 false', () => {
    const store = useSongsStore()
    store.songs = []
    expect(store.hasSongs).toBe(false)
  })

  it('hasSongs: 有歌曲返回 true', () => {
    const store = useSongsStore()
    store.songs = [makeSong()]
    expect(store.hasSongs).toBe(true)
  })

  it('goToPage: 正常翻页', () => {
    const store = useSongsStore()
    store.total = 50
    store.goToPage(2)
    expect(store.currentPage).toBe(2)
  })

  it('goToPage: 低于下限保护', () => {
    const store = useSongsStore()
    store.total = 50
    store.currentPage = 2
    store.goToPage(0)
    expect(store.currentPage).toBe(1)
  })

  it('goToPage: 超出上限保护', () => {
    const store = useSongsStore()
    store.total = 10
    store.goToPage(999)
    expect(store.currentPage).toBe(1)
  })

  it('setSearch: 更新搜索词并重置页码', () => {
    const store = useSongsStore()
    store.currentPage = 3
    store.setSearch('月亮')
    expect(store.searchQuery).toBe('月亮')
    expect(store.currentPage).toBe(1)
  })

  it('setStyleFilter: 更新风格筛选并重置页码', () => {
    const store = useSongsStore()
    store.currentPage = 2
    store.setStyleFilter('pop')
    expect(store.styleFilter).toBe('pop')
    expect(store.currentPage).toBe(1)
  })

  it('setDifficultyFilter: 更新难度筛选并重置页码', () => {
    const store = useSongsStore()
    store.currentPage = 2
    store.setDifficultyFilter('advanced')
    expect(store.difficultyFilter).toBe('advanced')
    expect(store.currentPage).toBe(1)
  })

  it('resetFilters: 清空所有筛选并重置页码', () => {
    const store = useSongsStore()
    store.searchQuery = '月亮'
    store.styleFilter = 'pop'
    store.difficultyFilter = 'advanced'
    store.currentPage = 3
    store.resetFilters()
    expect(store.searchQuery).toBe('')
    expect(store.styleFilter).toBe('')
    expect(store.difficultyFilter).toBe('')
    expect(store.currentPage).toBe(1)
  })

  it('openUploadDialog: 打开上传对话框', () => {
    const store = useSongsStore()
    store.openUploadDialog()
    expect(store.showUploadDialog).toBe(true)
  })

  it('closeUploadDialog: 关闭对话框', () => {
    const store = useSongsStore()
    store.showUploadDialog = true
    store.closeUploadDialog()
    expect(store.showUploadDialog).toBe(false)
  })

  it('removeSongLocally: 从列表移除歌曲并递减 total', () => {
    const store = useSongsStore()
    store.songs = [makeSong({ id: 'aaa' }), makeSong({ id: 'bbb' })]
    store.total = 2
    store.removeSongLocally('aaa')
    expect(store.songs).toHaveLength(1)
    expect(store.songs[0].id).toBe('bbb')
    expect(store.total).toBe(1)
  })

  it('removeSongLocally: total 不会低于 0', () => {
    const store = useSongsStore()
    store.songs = []
    store.total = 0
    store.removeSongLocally('ghost')
    expect(store.total).toBe(0)
  })
})
