/**
 * pitchHeatmap 单元测试 — v7.13 Phase 5 偏差热力图
 *
 * 对齐 pitch-realtime.feature "对比分析 — 双轨叠加对比":
 *   - "底部应显示偏差热力图条 (一整行, 颜色密度表示跑调程度)"
 *   - "点击偏差热力图任意位置可跳转播放"
 *   And 低对齐段内的桶置灰 (不误导用户, 对齐 DTW 未对齐场景)
 */
import { describe, it, expect } from 'vitest'
import {
  computeHeatmapSegments,
  heatmapClickToTime,
  type HeatmapSegment,
} from '@/utils/pitchHeatmap'
import { DEVIATION_COLORS } from '@/utils/pitchDeviation'
import type { DeviationFrame } from '@/types/pitch'

/** 构造偏差帧 (absCentsDeviation 用于分桶统计) */
function frame(time: number, absCents: number, isSilent = false): DeviationFrame {
  return {
    time,
    frequency: isSilent ? 0 : 400,
    confidence: isSilent ? 0 : 1,
    refFrequency: 400,
    centsDeviation: absCents,
    absCentsDeviation: absCents,
    colorHex: isSilent ? DEVIATION_COLORS.silent : DEVIATION_COLORS.accurate,
    isSilent,
    isOctaveJump: false,
  }
}

describe('computeHeatmapSegments', () => {
  it('空帧 → []', () => {
    expect(computeHeatmapSegments([], 10, 4)).toEqual([])
  })

  it('totalDuration <= 0 → []', () => {
    expect(computeHeatmapSegments([frame(0, 10)], 0, 4)).toEqual([])
  })

  it('numBuckets < 1 → 钳制为 1', () => {
    const segs = computeHeatmapSegments([frame(0, 10), frame(1, 20)], 2, 0)
    expect(segs).toHaveLength(1)
    expect(segs[0].startTime).toBe(0)
    expect(segs[0].endTime).toBe(2)
  })

  it('分桶统计: 每桶 severity = 平均绝对偏差, outOfTuneFraction = 跑调帧占比', () => {
    // 0-1s 桶: 3 帧偏差 10/20/30 → severity 20, 无跑调
    // 1-2s 桶: 2 帧偏差 60/80 → severity 70, 跑调占比 1.0
    const frames = [frame(0.1, 10), frame(0.4, 20), frame(0.8, 30), frame(1.2, 60), frame(1.6, 80)]
    const segs = computeHeatmapSegments(frames, 2, 2)
    expect(segs).toHaveLength(2)
    expect(segs[0].severity).toBeCloseTo(20)
    expect(segs[0].outOfTuneFraction).toBe(0)
    expect(segs[1].severity).toBeCloseTo(70)
    expect(segs[1].outOfTuneFraction).toBe(1)
  })

  it('颜色 = deviationColor(平均偏差): ≤25 绿 / ≤50 橙 / >50 红', () => {
    const green = computeHeatmapSegments([frame(0.1, 20)], 1, 1)[0]
    expect(green.color).toBe(DEVIATION_COLORS.accurate)
    const orange = computeHeatmapSegments([frame(0.1, 40)], 1, 1)[0]
    expect(orange.color).toBe(DEVIATION_COLORS.slightBias)
    const red = computeHeatmapSegments([frame(0.1, 70)], 1, 1)[0]
    expect(red.color).toBe(DEVIATION_COLORS.outOfTune)
  })

  it('静音帧不参与 severity 统计', () => {
    const frames = [frame(0.1, 10, true), frame(0.4, 30)]
    const segs = computeHeatmapSegments(frames, 1, 1)
    expect(segs[0].severity).toBeCloseTo(30)
  })

  it('空桶 (无有效帧) → 灰色 + severity 0', () => {
    const frames = [frame(0.1, 10)]
    const segs = computeHeatmapSegments(frames, 4, 4)
    expect(segs[3].color).toBe(DEVIATION_COLORS.silent)
    expect(segs[3].severity).toBe(0)
  })

  it('落在低对齐段内的桶 → 灰色 (不误导)', () => {
    const frames = [frame(0.5, 70)] // 高偏差, 本应红色
    const lowSegs = [{ start: 0.0, end: 1.0, avgConfidence: 0.3 }]
    const segs = computeHeatmapSegments(frames, 2, 2, lowSegs)
    expect(segs[0].color).toBe(DEVIATION_COLORS.silent)
  })
})

describe('heatmapClickToTime', () => {
  it('0 → 0; 1 → totalDuration; 0.5 → 中点', () => {
    expect(heatmapClickToTime(0, 120)).toBe(0)
    expect(heatmapClickToTime(1, 120)).toBe(120)
    expect(heatmapClickToTime(0.5, 120)).toBe(60)
  })

  it('越界钳制到 [0, totalDuration]', () => {
    expect(heatmapClickToTime(-1, 120)).toBe(0)
    expect(heatmapClickToTime(2, 120)).toBe(120)
  })

  it('totalDuration <= 0 → 0', () => {
    expect(heatmapClickToTime(0.5, 0)).toBe(0)
  })
})

// 类型导出健全性 (供组件使用)
export type { HeatmapSegment }
