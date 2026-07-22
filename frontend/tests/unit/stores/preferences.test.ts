/**
 * preferences.store — 单元测试
 *
 * 测试: 默认值、主题切换、评估模式、持久化
 */

import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { usePreferencesStore } from '@/stores/preferences.store'

// happy-dom requires explicit localStorage polyfill
const storage = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (key: string) => storage.get(key) ?? null,
  setItem: (key: string, value: string) => { storage.set(key, value) },
  removeItem: (key: string) => { storage.delete(key) },
  clear: () => { storage.clear() },
  get length() { return storage.size },
  key: (i: number) => [...storage.keys()][i] ?? null,
})

describe('usePreferencesStore', () => {
  beforeEach(() => {
    storage.clear()
    setActivePinia(createPinia())
  })

  it('默认主题为 light', () => {
    const store = usePreferencesStore()
    expect(store.theme).toBe('light')
  })

  it('默认评估模式为 quick', () => {
    const store = usePreferencesStore()
    expect(store.evalMode).toBe('quick')
  })

  it('默认 autoPlay 为 true', () => {
    const store = usePreferencesStore()
    expect(store.autoPlay).toBe(true)
  })

  it('默认 autoNavigate 为 true', () => {
    const store = usePreferencesStore()
    expect(store.autoNavigate).toBe(true)
  })

  it('toggleTheme 切换主题', () => {
    const store = usePreferencesStore()
    expect(store.theme).toBe('light')
    store.toggleTheme()
    expect(store.theme).toBe('dark')
    store.toggleTheme()
    expect(store.theme).toBe('light')
  })

  it('setTheme 设置主题', () => {
    const store = usePreferencesStore()
    store.setTheme('dark')
    expect(store.theme).toBe('dark')
    store.setTheme('light')
    expect(store.theme).toBe('light')
  })

  it('setEvalMode 设置评估模式', () => {
    const store = usePreferencesStore()
    store.setEvalMode('professional')
    expect(store.evalMode).toBe('professional')
    store.setEvalMode('quick')
    expect(store.evalMode).toBe('quick')
  })

  it('setAutoPlay 切换自动播放', () => {
    const store = usePreferencesStore()
    store.setAutoPlay(false)
    expect(store.autoPlay).toBe(false)
    store.setAutoPlay(true)
    expect(store.autoPlay).toBe(true)
  })

  it('setAutoNavigate 切换自动跳转', () => {
    const store = usePreferencesStore()
    store.setAutoNavigate(false)
    expect(store.autoNavigate).toBe(false)
  })

  it('偏好设置持久化到 localStorage', () => {
    const store1 = usePreferencesStore()
    store1.setTheme('dark')
    store1.setEvalMode('professional')
    store1.setAutoPlay(false)

    // 第二个 store 实例应读取已持久化的值
    const raw = localStorage.getItem('vas-preferences')
    expect(raw).not.toBeNull()

    const parsed = JSON.parse(raw!)
    expect(parsed.theme).toBe('dark')
    expect(parsed.evalMode).toBe('professional')
    expect(parsed.autoPlay).toBe(false)
  })
})
