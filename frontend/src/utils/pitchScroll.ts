/**
 * 音准曲线滚动窗口 — v7.13 实时音准对比
 *
 * 纯函数, 零 Vue 依赖, 可直接 Vitest 测试。
 * 全民K歌式滚动: 播放位置居中, 从右向左滚动。
 */
import type { PitchPoint } from '@/types/pitch'

/** 长音频默认视口 (秒) — pitch-realtime.feature */
export const DEFAULT_VIEWPORT_SECONDS = 15
export const SHORT_AUDIO_THRESHOLD_SECONDS = 10

export interface ScrollWindowConfig {
  /** 视口宽度 (秒) */
  viewportSeconds: number
  /** 总时长 (秒) */
  totalDuration: number
  /** 当前播放位置 (秒) */
  currentTime: number
}

export interface ScrollWindowResult {
  /** 视口起始时间 */
  windowStart: number
  /** 视口结束时间 */
  windowEnd: number
  /** 播放竖线在视口中的相对位置 (0-1) */
  cursorXFraction: number
}

/** 计算滚动视口 — 播放位置尽量居中, 边界钳制 */
export function computeScrollWindow(config: ScrollWindowConfig): ScrollWindowResult {
  const { viewportSeconds, totalDuration, currentTime } = config
  const safeViewport = Math.max(1, viewportSeconds)

  // 视口大于总时长 → 全曲可见
  if (totalDuration <= safeViewport) {
    const frac = totalDuration > 0 ? clamp01(currentTime / totalDuration) : 0
    return { windowStart: 0, windowEnd: totalDuration, cursorXFraction: frac }
  }

  const rawStart = currentTime - safeViewport / 2
  const windowStart = clamp(rawStart, 0, totalDuration - safeViewport)
  const windowEnd = windowStart + safeViewport
  const frac = clamp01((currentTime - windowStart) / safeViewport)

  return { windowStart, windowEnd, cursorXFraction: frac }
}

/** 播放竖线在视口中的 X 位置 (独立实现, 0-1) */
export function cursorXFraction(currentTime: number, windowStart: number, windowEnd: number): number {
  const width = windowEnd - windowStart
  if (width <= 0) return 0
  return clamp01((currentTime - windowStart) / width)
}

/** 首尾静音裁剪 — 返回首个/末个有效帧索引 (全静音 → endIdx < startIdx) */
export function trimSilence(frames: PitchPoint[]): { startIdx: number; endIdx: number } {
  let startIdx = 0
  let endIdx = frames.length - 1

  while (startIdx < frames.length && frames[startIdx].frequency <= 0) startIdx++
  while (endIdx >= 0 && frames[endIdx].frequency <= 0) endIdx--

  // 全静音 → 空区间 (endIdx < startIdx 约定)
  if (startIdx > endIdx) return { startIdx: 0, endIdx: -1 }

  return { startIdx, endIdx }
}

/** 自动视口宽度 — 短音频 (≤10s) 全曲, 长音频 15s */
export function autoViewportSeconds(totalDuration: number): number {
  if (totalDuration <= SHORT_AUDIO_THRESHOLD_SECONDS) return totalDuration
  return DEFAULT_VIEWPORT_SECONDS
}

/**
 * 自动时间刻度步长 (秒) — X 轴标注。
 * 短音频 1s/格, 中等 5s, 长音频 15s。
 */
export function autoTickStepSeconds(totalDuration: number): number {
  if (totalDuration <= 0) return 1
  if (totalDuration <= SHORT_AUDIO_THRESHOLD_SECONDS) return 1
  if (totalDuration <= 60) return 5
  return 15
}

/** 生成 [0, totalDuration] 内步长 timeStep 的时间刻度 (含端点, 不超范围) */
export function generateTimeTicks(totalDuration: number, timeStep: number): number[] {
  if (totalDuration <= 0 || timeStep <= 0) return []
  const ticks: number[] = []
  for (let t = 0; t <= totalDuration; t += timeStep) {
    ticks.push(t)
  }
  return ticks
}

function clamp(v: number, lo: number, hi: number): number {
  return Math.max(lo, Math.min(hi, v))
}

function clamp01(v: number): number {
  return clamp(v, 0, 1)
}
