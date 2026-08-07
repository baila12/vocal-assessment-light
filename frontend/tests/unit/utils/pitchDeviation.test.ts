/**
 * pitchDeviation 单元测试 — v7.13 实时音准偏差计算
 *
 * 纯函数: cents 偏差 / 颜色映射 / 八度跳变 / 曲线对齐。
 */
import { describe, it, expect } from 'vitest'
import {
  freqToCents,
  deviationColor,
  isOctaveJump,
  alignPitchCurves,
  DEVIATION_COLORS,
} from '@/utils/pitchDeviation'
import type { PitchPoint } from '@/types/pitch'

describe('freqToCents', () => {
  it('相同频率 → 0 音分', () => {
    expect(freqToCents(440, 440)).toBeCloseTo(0, 5)
  })

  it('高一个八度 → +1200 音分', () => {
    expect(freqToCents(880, 440)).toBeCloseTo(1200, 5)
  })

  it('低一个八度 → -1200 音分', () => {
    expect(freqToCents(220, 440)).toBeCloseTo(-1200, 5)
  })

  it('参考频率为 0 (无声) → 0 音分', () => {
    expect(freqToCents(440, 0)).toBe(0)
  })

  it('用户频率为 0 (无声) → 0 音分', () => {
    expect(freqToCents(0, 440)).toBe(0)
  })
})

describe('deviationColor', () => {
  it('≤25 音分 → 精准绿', () => {
    expect(deviationColor(0)).toBe(DEVIATION_COLORS.accurate)
    expect(deviationColor(25)).toBe(DEVIATION_COLORS.accurate)
  })

  it('25-50 音分 → 略偏橙', () => {
    expect(deviationColor(30)).toBe(DEVIATION_COLORS.slightBias)
    expect(deviationColor(50)).toBe(DEVIATION_COLORS.slightBias)
  })

  it('>50 音分 → 跑调红', () => {
    expect(deviationColor(50.1)).toBe(DEVIATION_COLORS.outOfTune)
    expect(deviationColor(200)).toBe(DEVIATION_COLORS.outOfTune)
  })
})

describe('isOctaveJump', () => {
  it('相差 ≥12 半音 → true (八度跳变)', () => {
    expect(isOctaveJump(220, 440)).toBe(true) // 12 半音
    expect(isOctaveJump(261.6, 523.2)).toBe(true)
  })

  it('相邻半音 → false', () => {
    expect(isOctaveJump(261.6, 277.2)).toBe(false)
  })

  it('任一帧无声 (0) → false', () => {
    expect(isOctaveJump(0, 440)).toBe(false)
    expect(isOctaveJump(440, 0)).toBe(false)
  })
})

describe('alignPitchCurves', () => {
  const refCurve: PitchPoint[] = [
    { time: 0.0, frequency: 440, confidence: 1 },
    { time: 0.5, frequency: 440, confidence: 1 },
    { time: 1.0, frequency: 440, confidence: 1 },
  ]

  it('音准一致 → 偏差 0, 绿色', () => {
    const user: PitchPoint[] = [
      { time: 0.25, frequency: 440, confidence: 1 },
    ]
    const frames = alignPitchCurves(user, refCurve)
    expect(frames[0].centsDeviation).toBeCloseTo(0, 3)
    expect(frames[0].colorHex).toBe(DEVIATION_COLORS.accurate)
  })

  it('偏高一个八度 → ~+1200 音分, 红色', () => {
    const user: PitchPoint[] = [
      { time: 0.25, frequency: 880, confidence: 1 },
    ]
    const frames = alignPitchCurves(user, refCurve)
    expect(frames[0].centsDeviation).toBeCloseTo(1200, 3)
    expect(frames[0].colorHex).toBe(DEVIATION_COLORS.outOfTune)
  })

  it('用户无声 → isSilent=true, 灰色', () => {
    const user: PitchPoint[] = [
      { time: 0.25, frequency: 0, confidence: 0.1 },
    ]
    const frames = alignPitchCurves(user, refCurve)
    expect(frames[0].isSilent).toBe(true)
    expect(frames[0].colorHex).toBe(DEVIATION_COLORS.silent)
  })

  it('参考无声 → 偏差 0, 灰色', () => {
    const emptyRef: PitchPoint[] = [
      { time: 0.0, frequency: 0, confidence: 0.1 },
      { time: 1.0, frequency: 0, confidence: 0.1 },
    ]
    const user: PitchPoint[] = [{ time: 0.5, frequency: 440, confidence: 1 }]
    const frames = alignPitchCurves(user, emptyRef)
    expect(frames[0].isSilent).toBe(true)
  })

  it('无参考曲线 → 偏差 0, 蓝色 (无对比)', () => {
    const user: PitchPoint[] = [{ time: 0.25, frequency: 440, confidence: 1 }]
    const frames = alignPitchCurves(user, [])
    expect(frames[0].centsDeviation).toBe(0)
    expect(frames[0].colorHex).toBe(DEVIATION_COLORS.silent)
  })

  it('置信度 < 0.5 → 视为无声 (气声/清辅音), 灰色', () => {
    const user: PitchPoint[] = [
      { time: 0.25, frequency: 440, confidence: 0.3 },
    ]
    const frames = alignPitchCurves(user, refCurve)
    expect(frames[0].isSilent).toBe(true)
    expect(frames[0].colorHex).toBe(DEVIATION_COLORS.silent)
    expect(frames[0].centsDeviation).toBe(0) // 不标记为跑调
  })

  it('置信度 ≥ 0.5 → 正常参与偏差计算', () => {
    const user: PitchPoint[] = [
      { time: 0.25, frequency: 440, confidence: 0.5 },
    ]
    const frames = alignPitchCurves(user, refCurve)
    expect(frames[0].isSilent).toBe(false)
    expect(frames[0].centsDeviation).toBeCloseTo(0, 3)
  })

  it('参考线按时间线性插值', () => {
    // ref: 0s→440, 2s→880 (线性)
    const sweepRef: PitchPoint[] = [
      { time: 0, frequency: 440, confidence: 1 },
      { time: 2, frequency: 880, confidence: 1 },
    ]
    const user: PitchPoint[] = [{ time: 1.0, frequency: 660, confidence: 1 }]
    const frames = alignPitchCurves(user, sweepRef)
    expect(frames[0].refFrequency).toBeCloseTo(660, 3)
    expect(frames[0].centsDeviation).toBeCloseTo(0, 3)
  })
})
