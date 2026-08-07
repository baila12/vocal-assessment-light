/**
 * 音准偏差计算 — v7.13 实时音准对比
 *
 * 纯函数, 零 Vue 依赖, 可直接 Vitest 测试。
 * 色彩规范 (pitch-realtime.feature):
 *   ≤25 音分 → 精准绿 #22c55e
 *   25-50    → 略偏橙 #f59e0b
 *   >50      → 跑调红 #ef4444
 *   无声     → 灰 #94a3b8
 */
import type { DeviationFrame, PitchPoint } from '@/types/pitch'

export const DEVIATION_THRESHOLDS = {
  accurate: 25,
  slightBias: 50,
  silentConfidence: 0.5,
  octaveJumpSemitones: 12,
} as const

export const DEVIATION_COLORS = {
  accurate: '#22c55e',
  slightBias: '#f59e0b',
  outOfTune: '#ef4444',
  silent: '#94a3b8',
} as const

/** 默认用户曲线颜色 (无参考时) */
export const DEFAULT_USER_COLOR = '#3b82f6'

/** 计算两频率间的音分偏差 (正=偏高) */
export function freqToCents(userFreq: number, refFreq: number): number {
  if (userFreq <= 0 || refFreq <= 0) return 0
  return 1200 * Math.log2(userFreq / refFreq)
}

/** 偏差颜色映射 */
export function deviationColor(absCents: number): string {
  if (absCents <= DEVIATION_THRESHOLDS.accurate) return DEVIATION_COLORS.accurate
  if (absCents <= DEVIATION_THRESHOLDS.slightBias) return DEVIATION_COLORS.slightBias
  return DEVIATION_COLORS.outOfTune
}

/** 八度跳变检测 — 相邻有效帧相差 ≥12 半音 */
export function isOctaveJump(prevFreq: number, currFreq: number): boolean {
  if (prevFreq <= 0 || currFreq <= 0) return false
  return Math.abs(1200 * Math.log2(currFreq / prevFreq)) >=
    DEVIATION_THRESHOLDS.octaveJumpSemitones * 100
}

/**
 * 参考曲线按时间线性插值 — 在 refCurve 中二分定位 t 附近的帧。
 * 无有效参考 → null。
 */
function interpolateRefFrequency(refCurve: PitchPoint[], t: number): number | null {
  if (refCurve.length === 0) return null

  // 二分查找: 找到最后一个 time <= t 的帧
  let lo = 0
  let hi = refCurve.length - 1
  if (t <= refCurve[0].time) return refCurve[0].frequency
  if (t >= refCurve[hi].time) return refCurve[hi].frequency

  while (lo < hi) {
    const mid = (lo + hi + 1) >> 1
    if (refCurve[mid].time <= t) lo = mid
    else hi = mid - 1
  }

  const a = refCurve[lo]
  const b = refCurve[lo + 1]
  if (b.time - a.time <= 1e-9) return a.frequency

  const frac = (t - a.time) / (b.time - a.time)
  return a.frequency + frac * (b.frequency - a.frequency)
}

/**
 * 用户曲线对齐到参考曲线 → 逐帧偏差
 *
 * 无参考曲线: refFrequency=0, cents=0, 灰色。
 */
export function alignPitchCurves(
  userFrames: PitchPoint[],
  refCurve: PitchPoint[],
): DeviationFrame[] {
  const frames: DeviationFrame[] = []

  for (let i = 0; i < userFrames.length; i++) {
    const u = userFrames[i]
    const refFreq = interpolateRefFrequency(refCurve, u.time)
    // 无声判定: 频率≤0 / 置信度<0.5 (气声、清辅音) / 无有效参考
    const isSilent =
      u.frequency <= 0 ||
      (u.confidence ?? 0) < DEVIATION_THRESHOLDS.silentConfidence ||
      refFreq === null ||
      refFreq <= 0

    let cents = 0
    if (!isSilent) {
      cents = freqToCents(u.frequency, refFreq)
    }

    const prev = i > 0 ? userFrames[i - 1] : null
    const octaveJump = prev !== null && isOctaveJump(prev.frequency, u.frequency)

    frames.push({
      time: u.time,
      frequency: u.frequency,
      confidence: u.confidence,
      refFrequency: isSilent ? 0 : (refFreq as number),
      centsDeviation: cents,
      absCentsDeviation: Math.abs(cents),
      colorHex: isSilent ? DEVIATION_COLORS.silent : deviationColor(Math.abs(cents)),
      isSilent,
      isOctaveJump: octaveJump,
    })
  }

  return frames
}
