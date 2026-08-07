/**
 * FPS 监控与降级状态机 — v7.13 Phase 5 渲染帧率保障 + 低性能设备降级
 *
 * 纯逻辑, 零 Vue 依赖, 可直接 Vitest 测试。
 * 对齐 pitch-realtime.feature:
 *   - "渲染帧率保障": 满帧率不降级; 持续低帧率自动降至 15fps 目标
 *   - "低性能设备降级": 连续 3s 帧率 < 20fps → 性能模式 + 手动切回画质模式
 *
 * 设计: 视图层提供 rAF 时间戳, 监控器维护滚动 1s 窗算出当前帧率,
 * 累计低帧率时长驱动 shouldDegradeFrameRate; 手动恢复后清除累计并可再次自动触发。
 * 所有状态访问返回不可变快照 (禁止外部 mutation)。
 */
import { LOW_FPS_THRESHOLD, shouldDegradeFrameRate } from '@/utils/pitchPlayback'

/** 降级目标帧率 (视图节流 rAF 目标) */
export { DEGRADE_TARGET_FPS } from '@/utils/pitchPlayback'

/** FPS 滚动窗 (ms) — 用于计算当前帧率 */
const FPS_WINDOW_MS = 1000

/** FPS 监控状态 (不可变快照) */
export interface FpsMonitorState {
  /** 当前帧率 (1s 滚动窗内帧数; 空窗 0) */
  readonly currentFps: number
  /** 性能模式已激活 */
  readonly isDegraded: boolean
  /** true=自动触发; false=用户手动恢复过画质模式 */
  readonly isAutoDegraded: boolean
  /** 连续低帧率累计时长 (秒) */
  readonly consecutiveLowFpsSeconds: number
}

/** FPS 监控器 — 创建独立实例供每个视图使用 */
export interface FpsMonitor {
  /** 记录一帧的时间戳 (ms) → 返回最新状态 */
  recordFrame(nowMs: number): FpsMonitorState
  /** 手动恢复画质模式 (幂等) → 返回最新状态 */
  restoreQualityMode(): FpsMonitorState
  /**
   * 重置时间基准 (后台恢复/长时间停顿后调用) — 清空滚动窗与低帧率连段,
   * 但不改变降级状态 (已降级设备保持降级)。防止把切 Tab 的间隙误计为持续低帧率。
   */
  resetTime(nowMs: number): FpsMonitorState
  /** 读取当前状态 (新对象, 不共享引用) */
  getState(): FpsMonitorState
}

interface FpsMonitorInternal {
  fps: number
  frameTimes: number[]
  /** 低帧率连段起始时间戳 (ms); 满帧率时 null */
  lowFpsStreakStart: number | null
  isDegraded: boolean
  isAutoDegraded: boolean
  lastFrameAt: number | null
}

/** 低帧率累计时长 (秒) — 由连段起始时间戳精确推得 (无浮点累加漂移) */
function lowFpsSeconds(s: FpsMonitorInternal): number {
  if (s.lowFpsStreakStart === null) return 0
  const end = s.lastFrameAt ?? s.lowFpsStreakStart
  return (end - s.lowFpsStreakStart) / 1000
}

function snapshot(s: FpsMonitorInternal): FpsMonitorState {
  return {
    currentFps: s.fps,
    isDegraded: s.isDegraded,
    isAutoDegraded: s.isAutoDegraded,
    consecutiveLowFpsSeconds: lowFpsSeconds(s),
  }
}

function computeFps(s: FpsMonitorInternal, nowMs: number): void {
  if (Number.isNaN(nowMs) || nowMs < 0) return
  if (s.lastFrameAt === null) {
    s.lastFrameAt = nowMs
    s.fps = 0
    return
  }
  const dtMs = nowMs - s.lastFrameAt
  s.lastFrameAt = nowMs
  if (dtMs <= 0) return

  // 滚动窗: 保留 1s 内的帧时间戳
  s.frameTimes.push(nowMs)
  const cutoff = nowMs - FPS_WINDOW_MS
  while (s.frameTimes.length > 0 && s.frameTimes[0] < cutoff) {
    s.frameTimes.shift()
  }
  const fps = s.frameTimes.length
  s.fps = fps

  // 低帧率连段: 满帧率 (≥ 阈值) 清零起始点; 低帧率记录起始并判断降级
  if (fps >= LOW_FPS_THRESHOLD) {
    s.lowFpsStreakStart = null
  } else {
    if (s.lowFpsStreakStart === null) s.lowFpsStreakStart = nowMs - dtMs
    if (shouldDegradeFrameRate(fps, lowFpsSeconds(s))) {
      s.isDegraded = true
      s.isAutoDegraded = true
    }
  }
}

/** 创建 FPS 监控器 */
export function createFpsMonitor(): FpsMonitor {
  const s: FpsMonitorInternal = {
    fps: 0,
    frameTimes: [],
    lowFpsStreakStart: null,
    isDegraded: false,
    isAutoDegraded: false,
    lastFrameAt: null,
  }

  return {
    recordFrame(nowMs: number): FpsMonitorState {
      computeFps(s, nowMs)
      return snapshot(s)
    },
    restoreQualityMode(): FpsMonitorState {
      s.isDegraded = false
      s.isAutoDegraded = false
      s.lowFpsStreakStart = null
      return snapshot(s)
    },
    resetTime(nowMs: number): FpsMonitorState {
      if (Number.isNaN(nowMs) || nowMs < 0) return snapshot(s)
      s.lastFrameAt = nowMs
      s.frameTimes = []
      s.fps = 0
      s.lowFpsStreakStart = null
      return snapshot(s)
    },
    getState(): FpsMonitorState {
      return snapshot(s)
    },
  }
}
