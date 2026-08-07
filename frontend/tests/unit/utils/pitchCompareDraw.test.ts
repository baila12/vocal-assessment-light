/**
 * pitchCompareDraw 单元测试 — v7.13 Phase 5 双轨叠加绘制
 *
 * 覆盖 pitch-realtime.feature:
 *   - 性能模式 "着色每 3 帧": drawDeviationCurve 降采样不丢曲线 (回归: 原实现计数器只进非跳过帧, 导致仅首帧被画)
 *   - 偏差区域填色: drawDeviationFillBands ≤25 绿 / 25-50 橙 / >50 红 (非 live 双轨)
 *   - 偏差背景色带: drawDeviationBands 三色隧道 (最外层红 >50, 再橙, 最内绿)
 */
import { describe, it, expect, vi } from 'vitest'
import {
  drawDeviationCurve,
  drawDeviationFillBands,
  drawDeviationBands,
} from '@/utils/pitchCompareDraw'
import type { DeviationFrame, PitchPoint } from '@/types/pitch'

/** 偏差帧构造器 — 省略字段给默认值 */
function frame(partial: Partial<DeviationFrame> & { time: number }): DeviationFrame {
  return {
    frequency: 0,
    confidence: 1,
    refFrequency: 0,
    centsDeviation: 0,
    absCentsDeviation: 0,
    colorHex: '#22c55e',
    isSilent: false,
    isOctaveJump: false,
    ...partial,
  }
}

interface FillCall {
  color: string
  x: number
  y: number
  w: number
  h: number
}

/** 绘制调用记录 — 记录 fillStyle/fillRect 时序与每次 fill() 时的当前填充色 */
function createMockCtx() {
  const fills: FillCall[] = []
  const fillColors: string[] = []
  let fillStyle = ''
  const ctx = {
    fillRect: vi.fn((x: number, y: number, w: number, h: number) => {
      fills.push({ color: fillStyle, x, y, w, h })
    }),
    fill: vi.fn(() => {
      fillColors.push(fillStyle)
    }),
    save: vi.fn(),
    restore: vi.fn(),
    beginPath: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    stroke: vi.fn(),
    closePath: vi.fn(),
    setLineDash: vi.fn(),
    get fillStyle() {
      return fillStyle
    },
    set fillStyle(v: string) {
      fillStyle = v
    },
    strokeStyle: '',
    globalAlpha: 1,
    lineWidth: 1,
    lineJoin: 'round',
  }
  return { ctx: ctx as unknown as CanvasRenderingContext2D, fills, fillColors }
}

describe('drawDeviationCurve — 性能模式每 3 帧着色', () => {
  it('性能模式下仍绘制约 1/3 的非静音帧 (回归: 原实现计数器只进非跳过帧 → 仅首帧被画)', () => {
    // 10 个连续同色有声帧 (时间 0..9)
    const frames: DeviationFrame[] = Array.from({ length: 10 }, (_, i) =>
      frame({ time: i, frequency: 220, refFrequency: 220, centsDeviation: 10, colorHex: '#22c55e' }),
    )
    const { ctx } = createMockCtx()
    const timeToX = (t: number): number => t * 10
    const freqToY = (f: number): number => 200 - f

    drawDeviationCurve(ctx, frames, timeToX, freqToY, 0, 9, true)

    // 每 3 帧取 1 → 画 3 个点 (1 moveTo + 2 lineTo); 若死锁只画首帧 → 仅 1 点 (0 lineTo)
    const pointCount = ctx.moveTo.mock.calls.length + ctx.lineTo.mock.calls.length
    expect(pointCount).toBe(3)
    expect(ctx.lineTo.mock.calls.length).toBe(2)
    expect(ctx.stroke).toHaveBeenCalledTimes(1)
  })

  it('非性能模式绘制全部 10 帧', () => {
    const frames: DeviationFrame[] = Array.from({ length: 10 }, (_, i) =>
      frame({ time: i, frequency: 220, refFrequency: 220, centsDeviation: 10, colorHex: '#22c55e' }),
    )
    const { ctx } = createMockCtx()
    drawDeviationCurve(ctx, frames, (t) => t * 10, (f) => 200 - f, 0, 9, false)
    const pointCount = ctx.moveTo.mock.calls.length + ctx.lineTo.mock.calls.length
    expect(pointCount).toBe(10)
  })

  it('性能模式下静音帧仍全部绘制 (灰虚线连续)', () => {
    // 交替: 有声→静音→有声... 静音帧不受降采样影响
    const frames: DeviationFrame[] = Array.from({ length: 8 }, (_, i) =>
      i % 2 === 0
        ? frame({ time: i, frequency: 220, refFrequency: 220, centsDeviation: 10, colorHex: '#22c55e' })
        : frame({ time: i, isSilent: true, frequency: 0, refFrequency: 220 }),
    )
    const { ctx } = createMockCtx()
    drawDeviationCurve(ctx, frames, (t) => t * 10, (f) => 200 - f, 0, 7, true)
    // 静音点 4 个 (1,3,5,7) 全画 → moveTo/lineTo 覆盖静音段
    const silentPointCount = ctx.moveTo.mock.calls.length + ctx.lineTo.mock.calls.length
    expect(silentPointCount).toBeGreaterThanOrEqual(3)
  })
})

describe('drawDeviationFillBands — 偏差区域三色填色', () => {
  it('按绝对音分偏差填色: ≤25 绿 / 25-50 橙 / >50 红, 槽宽为到下一帧的跨度', () => {
    const frames: DeviationFrame[] = [
      frame({ time: 0, frequency: 230, refFrequency: 220, centsDeviation: 10 }), // 绿
      frame({ time: 1, frequency: 250, refFrequency: 220, centsDeviation: 30 }), // 橙
      frame({ time: 2, frequency: 290, refFrequency: 220, centsDeviation: 70 }), // 红
    ]
    const { ctx, fills } = createMockCtx()
    drawDeviationFillBands({
      ctx,
      frames,
      timeToX: (t) => t * 10,
      freqToY: (f) => 200 - f,
      windowStart: 0,
      windowEnd: 5,
    })

    expect(fills).toHaveLength(3)
    expect(fills[0].color).toBe('rgba(34, 197, 94, 0.14)')
    expect(fills[0].w).toBe(10) // t0→t1 跨度
    expect(fills[1].color).toBe('rgba(245, 158, 11, 0.16)')
    expect(fills[1].w).toBe(10)
    expect(fills[2].color).toBe('rgba(239, 68, 68, 0.18)')
  })

  it('静音帧 / 无声帧 (frequency=0) / 窗口外帧不填色', () => {
    const frames: DeviationFrame[] = [
      frame({ time: 0, frequency: 230, refFrequency: 220, centsDeviation: 10 }),
      frame({ time: 1, isSilent: true, frequency: 0, refFrequency: 220 }),
      frame({ time: 2, frequency: 0, refFrequency: 220, centsDeviation: 20 }), // 无声
      frame({ time: 3, frequency: 230, refFrequency: 220, centsDeviation: 10 }), // 窗口外 (windowEnd=2)
    ]
    const { ctx, fills } = createMockCtx()
    drawDeviationFillBands({
      ctx,
      frames,
      timeToX: (t) => t * 10,
      freqToY: (f) => 200 - f,
      windowStart: 0,
      windowEnd: 2,
    })
    expect(fills).toHaveLength(1)
  })

  it('性能模式跳过填色 (降绘制开销)', () => {
    const frames: DeviationFrame[] = [
      frame({ time: 0, frequency: 230, refFrequency: 220, centsDeviation: 10 }),
    ]
    const { ctx, fills } = createMockCtx()
    drawDeviationFillBands({
      ctx,
      frames,
      timeToX: (t) => t * 10,
      freqToY: (f) => 200 - f,
      windowStart: 0,
      windowEnd: 5,
      performanceMode: true,
    })
    expect(fills).toHaveLength(0)
  })

  it('参考与用户重合的帧不填 (高度 < 0.5px, 视觉不可见)', () => {
    const frames: DeviationFrame[] = [
      frame({ time: 0, frequency: 220, refFrequency: 220, centsDeviation: 0 }),
    ]
    const { ctx, fills } = createMockCtx()
    drawDeviationFillBands({
      ctx,
      frames,
      timeToX: (t) => t * 10,
      freqToY: (f) => 200 - f,
      windowStart: 0,
      windowEnd: 5,
    })
    expect(fills).toHaveLength(0)
  })
})

describe('drawDeviationBands — 三色偏差背景隧道', () => {
  it('由外向内绘色带: 最外红 (>50) → 橙 (25-50) → 绿 (≤25), 叠出三色填色', () => {
    const ref: PitchPoint[] = [
      { time: 0, frequency: 440, confidence: 1 },
      { time: 1, frequency: 440, confidence: 1 },
    ]
    const { ctx, fillColors } = createMockCtx()
    drawDeviationBands(ctx, ref, (t) => t * 100, (f) => 400 - f, 0, 1)

    expect(fillColors).toHaveLength(3)
    expect(fillColors[0]).toBe('rgba(239, 68, 68, 0.06)') // 红最外层
    expect(fillColors[1]).toBe('rgba(245, 158, 11, 0.07)') // 橙
    expect(fillColors[2]).toBe('rgba(34, 197, 94, 0.10)') // 绿最内
  })
})
