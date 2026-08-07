/**
 * 录音中实时对比 — v7.13 Phase 3
 *
 * 纯函数, 零 Vue 依赖, 可直接 Vitest 测试。
 * 对齐 pitch-realtime.feature 第五节 Scenario "选歌录音 — 录音中实时对比":
 *   - 用户实时音高点 (每个音符 3px 圆点, 2 秒后淡出)
 *   - 偏差背景色带 (标准线上下 25/50 音分 绿色/橙色区域)
 *   - 当前音分偏差数值 (右上角 "+15 音分")
 *   - 音高趋势箭头 (偏高 ↑ 红 / 偏低 ↓ 蓝 / 精准 ✓ 绿)
 */
import { CENTS_PER_OCTAVE, DEVIATION_THRESHOLDS } from '@/utils/pitchDeviation'
import type { DeviationFrame, PitchPoint } from '@/types/pitch'

/** 圆点保留窗口 (秒) — feature: "圆点在 2 秒后淡出 (保留最近的音高轨迹)" */
export const LIVE_DOT_KEEP_SECONDS = 2
/** 淡出时长 (秒) — 到达保留窗口前最后 0.5s 线性淡出 */
export const LIVE_DOT_FADE_SECONDS = 0.5

/** 音高趋势: 偏高 / 偏低 / 精准 */
export type PitchTrend = 'high' | 'low' | 'on'

/** 趋势判定阈值 — 与偏差着色阈值一致 (|偏差| ≤25 音分 → 精准) */
export const TREND_THRESHOLD_CENTS = DEVIATION_THRESHOLDS.accurate

/** 趋势显示: 符号 + 颜色 + 文案 (feature: 偏高 ↑ 红 / 偏低 ↓ 蓝 / 精准 ✓ 绿) */
export const TREND_DISPLAY: Record<PitchTrend, { symbol: string; color: string; label: string }> = {
  high: { symbol: '↑', color: '#ef4444', label: '偏高' },
  low: { symbol: '↓', color: '#3b82f6', label: '偏低' },
  on: { symbol: '✓', color: '#22c55e', label: '精准' },
}

/** 音分偏差 → 趋势分类 */
export function deviationTrend(cents: number): PitchTrend {
  if (cents > TREND_THRESHOLD_CENTS) return 'high'
  if (cents < -TREND_THRESHOLD_CENTS) return 'low'
  return 'on'
}

/** 趋势 → 显示配置 (符号/颜色/文案) */
export function trendDisplay(trend: PitchTrend): { symbol: string; color: string; label: string } {
  return TREND_DISPLAY[trend]
}

/** 音分偏差 → 右上角显示文本 (如 "+15 音分" / "-12 音分"); 非有限值 → "-- 音分" */
export function formatCentsDeviation(cents: number): string {
  if (!Number.isFinite(cents)) return '-- 音分'
  const rounded = Math.round(cents)
  if (rounded === 0) return '0 音分'
  const sign = rounded > 0 ? '+' : '-'
  return `${sign}${Math.abs(rounded)} 音分`
}

/** 最近有声帧的音分偏差 — 用于当前趋势/数值显示; 全静音/空 → null */
export function latestDeviationCents(frames: DeviationFrame[]): number | null {
  for (let i = frames.length - 1; i >= 0; i--) {
    const f = frames[i]
    if (!f.isSilent) return f.centsDeviation
  }
  return null
}

/** 保留窗口内的音高点 (最近轨迹) — 排除未来点, 供圆点渲染 */
export function visibleLivePoints(
  points: PitchPoint[],
  now: number,
  keepSeconds: number = LIVE_DOT_KEEP_SECONDS,
): PitchPoint[] {
  if (keepSeconds <= 0) return []
  const cutoff = now - keepSeconds
  return points.filter((p) => p.time >= cutoff && p.time <= now)
}

/**
 * 圆点透明度 (0-1) — 按年龄线性淡出。
 * 未到淡出窗口 → 1; 进入最后 fadeSeconds → 线性衰减至 0。
 */
export function dotAlpha(
  age: number,
  keepSeconds: number = LIVE_DOT_KEEP_SECONDS,
  fadeSeconds: number = LIVE_DOT_FADE_SECONDS,
): number {
  if (!Number.isFinite(age) || age < 0) return 0
  if (age >= keepSeconds || keepSeconds <= 0 || fadeSeconds <= 0) return 0
  const remaining = keepSeconds - age
  if (remaining >= fadeSeconds) return 1
  return Math.max(0, remaining / fadeSeconds)
}

/** 频率的音分偏移 — 色带几何: freq * 2^(cents/CENTS_PER_OCTAVE); 非有限/非正 → 0 */
export function freqAtCentsOffset(freq: number, cents: number): number {
  if (!Number.isFinite(freq) || !Number.isFinite(cents) || freq <= 0) return 0
  return freq * Math.pow(2, cents / CENTS_PER_OCTAVE)
}
