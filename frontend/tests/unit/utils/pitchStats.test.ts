/**
 * pitchStats 单元测试 — v7.13 Phase 2 偏差统计与音域
 *
 * 纯函数: 偏差统计 (精准率/略偏率/跑调率/无声率) + 音域范围。
 * 对齐 pitch-realtime.feature:
 *   "播放结束后应显示统计: 精准率 78% | 略偏 15% | 跑调 7%"
 *   "最高音: G5" "最低音: C3"
 */
import { describe, it, expect } from 'vitest'
import {
  computeDeviationStats,
  computePitchRange,
  computeFramePercentages,
} from '@/utils/pitchStats'
import { DEVIATION_COLORS } from '@/utils/pitchDeviation'
import type { DeviationFrame, PitchPoint } from '@/types/pitch'

/** 构造偏差帧 — 只关注分类用字段 */
function frame(
  opts: Partial<DeviationFrame> & { colorHex: string },
): DeviationFrame {
  return {
    time: 0,
    frequency: 440,
    confidence: 1,
    refFrequency: 440,
    centsDeviation: 0,
    absCentsDeviation: 0,
    isSilent: false,
    isOctaveJump: false,
    ...opts,
  }
}

describe('computeFramePercentages', () => {
  it('按分类颜色统计百分比', () => {
    const frames = [
      frame({ colorHex: DEVIATION_COLORS.accurate }),   // 精准
      frame({ colorHex: DEVIATION_COLORS.accurate }),   // 精准
      frame({ colorHex: DEVIATION_COLORS.slightBias }), // 略偏
      frame({ colorHex: DEVIATION_COLORS.outOfTune }),  // 跑调
      frame({ colorHex: DEVIATION_COLORS.silent }),     // 无声
    ]
    const p = computeFramePercentages(frames)
    expect(p.accuratePct).toBe(40)
    expect(p.slightPct).toBe(20)
    expect(p.outOfTunePct).toBe(20)
    expect(p.silentPct).toBe(20)
  })

  it('空数组 → 全 0', () => {
    const p = computeFramePercentages([])
    expect(p.accuratePct).toBe(0)
    expect(p.slightPct).toBe(0)
    expect(p.outOfTunePct).toBe(0)
    expect(p.silentPct).toBe(0)
  })

  it('未知颜色归类为无声 (安全兜底)', () => {
    const p = computeFramePercentages([frame({ colorHex: '#000000' })])
    expect(p.silentPct).toBe(100)
  })
})

describe('computeDeviationStats', () => {
  it('全精准 → 精准率 100%', () => {
    const frames = [
      frame({ colorHex: DEVIATION_COLORS.accurate }),
      frame({ colorHex: DEVIATION_COLORS.accurate }),
      frame({ colorHex: DEVIATION_COLORS.accurate }),
    ]
    const s = computeDeviationStats(frames)
    expect(s.accuratePct).toBe(100)
    expect(s.slightPct).toBe(0)
    expect(s.outOfTunePct).toBe(0)
  })

  it('混合 78/15/7 → 精准率 78%, 略偏 15%, 跑调 7%', () => {
    // 200 帧: 156 精准 + 30 略偏 + 14 跑调 (无声 0)
    const frames = [
      ...Array.from({ length: 156 }, () => frame({ colorHex: DEVIATION_COLORS.accurate })),
      ...Array.from({ length: 30 }, () => frame({ colorHex: DEVIATION_COLORS.slightBias })),
      ...Array.from({ length: 14 }, () => frame({ colorHex: DEVIATION_COLORS.outOfTune })),
    ]
    const s = computeDeviationStats(frames)
    expect(s.accuratePct).toBe(78)
    expect(s.slightPct).toBe(15)
    expect(s.outOfTunePct).toBe(7)
  })

  it('无声帧计入无声率, 不参与有声音准比例', () => {
    const frames = [
      frame({ colorHex: DEVIATION_COLORS.accurate }),
      frame({ colorHex: DEVIATION_COLORS.accurate }),
      frame({ colorHex: DEVIATION_COLORS.silent }),
      frame({ colorHex: DEVIATION_COLORS.silent }),
    ]
    const s = computeDeviationStats(frames)
    expect(s.silentPct).toBe(50)
    expect(s.accuratePct).toBe(100) // 有声帧全部精准
  })

  it('无有效帧 (全部无声) → 精准率 0 而非 NaN', () => {
    const s = computeDeviationStats([
      frame({ colorHex: DEVIATION_COLORS.silent }),
    ])
    expect(s.accuratePct).toBe(0)
    expect(Number.isFinite(s.accuratePct)).toBe(true)
  })

  it('无声率取整不引入分母误差 — 有声帧精确计数 (审查回归)', () => {
    // 2000 帧: silent=501 → silentPct=round1(25.05)=25.1
    // 旧实现从 25.1 反推 voiced=round(2000×74.9/100)=1498 (差 1 帧)
    // 新实现精确计数 voiced=1499 → accuratePct=50.0 (旧实现会得 50.1)
    const frames = [
      ...Array.from({ length: 750 }, () => frame({ colorHex: DEVIATION_COLORS.accurate })),
      ...Array.from({ length: 375 }, () => frame({ colorHex: DEVIATION_COLORS.slightBias })),
      ...Array.from({ length: 374 }, () => frame({ colorHex: DEVIATION_COLORS.outOfTune })),
      ...Array.from({ length: 501 }, () => frame({ colorHex: DEVIATION_COLORS.silent })),
    ]
    const s = computeDeviationStats(frames)
    expect(s.silentPct).toBe(25.1)
    expect(s.accuratePct).toBe(50.0)
    expect(s.slightPct).toBe(25.0)
    expect(s.outOfTunePct).toBe(24.9)
  })
})

describe('computePitchRange', () => {
  it('返回最低/最高频率与音名', () => {
    const points: PitchPoint[] = [
      { time: 0, frequency: 261.63, confidence: 1 }, // C4
      { time: 1, frequency: 392.0, confidence: 1 },  // G4
      { time: 2, frequency: 0, confidence: 0.1 },    // 无声忽略
      { time: 3, frequency: 783.99, confidence: 1 }, // G5
    ]
    const r = computePitchRange(points)
    expect(r.minFreq).toBeCloseTo(261.63, 1)
    expect(r.maxFreq).toBeCloseTo(783.99, 1)
    expect(r.minNote).toBe('C4')
    expect(r.maxNote).toBe('G5')
  })

  it('全无声 → null', () => {
    const points: PitchPoint[] = [
      { time: 0, frequency: 0, confidence: 0.1 },
      { time: 1, frequency: 0, confidence: 0.1 },
    ]
    const r = computePitchRange(points)
    expect(r).toBeNull()
  })

  it('空数组 → null', () => {
    expect(computePitchRange([])).toBeNull()
  })
})
