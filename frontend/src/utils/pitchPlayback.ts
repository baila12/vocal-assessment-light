/**
 * 播放控制纯逻辑 — v7.13 Phase 2 音准对比视图播放
 *
 * 纯函数, 零 Vue 依赖, 可直接 Vitest 测试。
 * 对齐 pitch-realtime.feature 第三章 (播放控制):
 *   - 暂停冻结 / 拖拽钳制 / 倍速推进 / A-B 循环 / 帧率降级。
 */
import { SHORT_AUDIO_THRESHOLD_SECONDS } from '@/utils/pitchScroll'

/** 支持的播放倍速 */
export const PLAYBACK_RATES = [0.5, 1, 1.5] as const

/** 默认倍速 */
export const DEFAULT_PLAYBACK_RATE: number = 1

/** A-B 循环区间 (秒) */
export interface ABLoopRange {
  a: number
  b: number
}

/** 拖拽跳转目标时间 — 钳制到 [0, duration] */
export function clampSeek(target: number, duration: number): number {
  if (duration <= 0) return 0
  return Math.max(0, Math.min(duration, target))
}

export interface AdvancePlaybackParams {
  /** 当前时间 (秒) */
  current: number
  /** 时间增量 (秒) */
  dt: number
  /** 倍速 (0=暂停, 0.5/1/1.5) */
  rate: number
  /** 总时长 (秒) */
  duration: number
}

/**
 * 播放推进 — 当前时间 + dt*rate, 钳制到 [0, duration]。
 * rate=0 时冻结 (暂停); 倍速缩放滚动速度。
 */
export function advancePlayback({ current, dt, rate, duration }: AdvancePlaybackParams): number {
  if (duration <= 0) return 0
  const next = current + dt * rate
  return Math.max(0, Math.min(duration, next))
}

/** 是否在 A-B 循环区间内 */
export function isInABLoop(time: number, loop: ABLoopRange | null): boolean {
  if (!loop || loop.b <= loop.a) return false
  return time >= loop.a && time <= loop.b
}

/** A-B 循环回绕 — 越过 B 点回绕到 A (无缝) */
export function wrapInABLoop(time: number, loop: ABLoopRange | null): number {
  if (!loop || loop.b <= loop.a) return time
  const span = loop.b - loop.a
  if (time < loop.a) return loop.b - ((loop.a - time) % span)
  if (time > loop.b) return loop.a + ((time - loop.b) % span)
  return time
}

/** 渲染降级阈值 — 连续 lowFpsDurationSeconds 秒帧率低于阈值则降级 */
export const LOW_FPS_THRESHOLD = 20
export const LOW_FPS_DURATION_SECONDS = 3
export const DEGRADE_TARGET_FPS = 15

/**
 * 是否应降级渲染 — 连续 ≥3 秒帧率 < 20fps。
 * 对齐 feature: "连续 3 秒帧率 < 20fps → 自动切换性能模式"。
 */
export function shouldDegradeFrameRate(
  fps: number,
  lowFpsDurationSeconds: number,
): boolean {
  if (fps <= 0 || lowFpsDurationSeconds <= 0) return false
  return fps < LOW_FPS_THRESHOLD && lowFpsDurationSeconds >= LOW_FPS_DURATION_SECONDS
}

/** 渲染降级目标帧率 */
export function degradeTargetFps(): number {
  return DEGRADE_TARGET_FPS
}

/** 短音频判定 (≤10s) — 供视口/刻度选择 */
export function isShortAudio(duration: number): boolean {
  return duration > 0 && duration <= SHORT_AUDIO_THRESHOLD_SECONDS
}
