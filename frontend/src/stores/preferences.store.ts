/**
 * 用户偏好状态管理 — Pinia store (persisted)
 *
 * 管理：主题、默认评估模式、自动播放、自动跳转
 * 持久化到 localStorage，Electron + 浏览器通用
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ThemeMode = 'light' | 'dark'
export type EvalMode = 'quick' | 'professional'

const STORAGE_KEY = 'vas-preferences'

const hasStorage = typeof localStorage !== 'undefined'

function loadFromStorage(): Record<string, unknown> {
  if (!hasStorage) return {}
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveToStorage(data: Record<string, unknown>): void {
  if (!hasStorage) return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  } catch {
    // Storage full or unavailable — silently ignore
  }
}

export const usePreferencesStore = defineStore('preferences', () => {
  const saved = loadFromStorage()

  // ---- 状态 (从 localStorage 恢复) ----
  const theme = ref<ThemeMode>((saved.theme as ThemeMode) || 'light')
  const evalMode = ref<EvalMode>((saved.evalMode as EvalMode) || 'quick')
  const autoPlay = ref<boolean>(saved.autoPlay !== false) // default true
  const autoNavigate = ref<boolean>(saved.autoNavigate !== false) // default true

  // ---- 操作 ----
  function applyTheme(): void {
    if (typeof document !== 'undefined') {
      document.documentElement.classList.toggle('dark', theme.value === 'dark')
    }
  }

  function toggleTheme(): void {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    applyTheme()
    persist()
  }

  function setTheme(mode: ThemeMode): void {
    theme.value = mode
    applyTheme()
    persist()
  }

  function setEvalMode(mode: EvalMode): void {
    evalMode.value = mode
    persist()
  }

  function setAutoPlay(value: boolean): void {
    autoPlay.value = value
    persist()
  }

  function setAutoNavigate(value: boolean): void {
    autoNavigate.value = value
    persist()
  }

  function persist(): void {
    saveToStorage({
      theme: theme.value,
      evalMode: evalMode.value,
      autoPlay: autoPlay.value,
      autoNavigate: autoNavigate.value,
    })
  }

  // 初始化时应用主题
  applyTheme()

  return {
    theme,
    evalMode,
    autoPlay,
    autoNavigate,
    toggleTheme,
    setTheme,
    setEvalMode,
    setAutoPlay,
    setAutoNavigate,
  }
})
