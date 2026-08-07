/**
 * 偏差统计与音域 — v7.13 Phase 2 音准对比统计
 *
 * 纯函数, 零 Vue 依赖, 可直接 Vitest 测试。
 * 对齐 pitch-realtime.feature:
 *   - 播放结束后显示 "精准率 78% | 略偏 15% | 跑调 7%"
 *   - 曲线上标注 "最高音: G5" "最低音: C3"
 */
import { DEVIATION_COLORS } from '@/utils/pitchDeviation'
import { freqToNoteName } from '@/utils/pitchNotes'
import type { DeviationFrame, PitchPoint } from '@/types/pitch'

export interface DeviationPercentages {
  /** 精准率 (%) — 偏差 ≤25 音分 */
  accuratePct: number
  /** 略偏率 (%) — 25-50 音分 */
  slightPct: number
  /** 跑调率 (%) — >50 音分 */
  outOfTunePct: number
  /** 无声率 (%) */
  silentPct: number
}

const EMPTY_PCT: DeviationPercentages = {
  accuratePct: 0,
  slightPct: 0,
  outOfTunePct: 0,
  silentPct: 0,
}

/** 按偏差颜色归类统计帧占比 (无声: 灰色/未分类) */
export function computeFramePercentages(frames: DeviationFrame[]): DeviationPercentages {
  if (frames.length === 0) return EMPTY_PCT

  let accurate = 0
  let slight = 0
  let outOfTune = 0
  let silent = 0

  for (const f of frames) {
    switch (f.colorHex) {
      case DEVIATION_COLORS.accurate:
        accurate++
        break
      case DEVIATION_COLORS.slightBias:
        slight++
        break
      case DEVIATION_COLORS.outOfTune:
        outOfTune++
        break
      default:
        silent++
        break
    }
  }

  const total = frames.length
  const round1 = (n: number): number => Math.round(n * 10) / 10
  return {
    accuratePct: round1((accurate / total) * 100),
    slightPct: round1((slight / total) * 100),
    outOfTunePct: round1((outOfTune / total) * 100),
    silentPct: round1((silent / total) * 100),
  }
}

/**
 * 偏差统计 — 有声帧按偏差比例 (无声帧独立成无声率)。
 * 无声率 = 无声帧 / 总帧; 有声三率 = 有声帧内的占比。
 */
export function computeDeviationStats(frames: DeviationFrame[]): DeviationPercentages {
  if (frames.length === 0) return EMPTY_PCT

  const pct = computeFramePercentages(frames)

  // 有声帧数 = 总帧 - 无声帧
  const voiced = Math.round((frames.length * (100 - pct.silentPct)) / 100)
  if (voiced <= 0) {
    return { ...EMPTY_PCT, silentPct: pct.silentPct }
  }

  // 重新按有声帧为分母计算三率
  const accurateCount = frames.filter((f) => f.colorHex === DEVIATION_COLORS.accurate).length
  const slightCount = frames.filter((f) => f.colorHex === DEVIATION_COLORS.slightBias).length
  const outOfTuneCount = frames.filter((f) => f.colorHex === DEVIATION_COLORS.outOfTune).length

  const round1 = (n: number): number => Math.round(n * 10) / 10
  return {
    accuratePct: round1((accurateCount / voiced) * 100),
    slightPct: round1((slightCount / voiced) * 100),
    outOfTunePct: round1((outOfTuneCount / voiced) * 100),
    silentPct: pct.silentPct,
  }
}

export interface PitchRange {
  /** 最低有效频率 (Hz) */
  minFreq: number
  /** 最高有效频率 (Hz) */
  maxFreq: number
  /** 最低音名 (如 'C3') */
  minNote: string
  /** 最高音名 (如 'G5') */
  maxNote: string
}

/** 音域范围 — 仅有效帧; 全无声/空 → null */
export function computePitchRange(points: PitchPoint[]): PitchRange | null {
  let minFreq = Infinity
  let maxFreq = -Infinity

  for (const p of points) {
    if (p.frequency <= 0) continue
    if (p.frequency < minFreq) minFreq = p.frequency
    if (p.frequency > maxFreq) maxFreq = p.frequency
  }

  if (!Number.isFinite(minFreq)) return null

  const minNote = freqToNoteName(minFreq)
  const maxNote = freqToNoteName(maxFreq)
  return {
    minFreq,
    maxFreq,
    minNote: minNote ?? '--',
    maxNote: maxNote ?? '--',
  }
}
