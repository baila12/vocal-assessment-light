/**
 * pitchScroll 单元测试 — v7.13 音准曲线滚动窗口
 *
 * 纯函数: 滚动视口 / 播放竖线位置 / 静音裁剪 / 自动视口。
 */
import { describe, it, expect } from 'vitest'
import {
  computeScrollWindow,
  cursorXFraction,
  trimSilence,
  autoViewportSeconds,
} from '@/utils/pitchScroll'
import type { PitchPoint } from '@/types/pitch'

describe('computeScrollWindow', () => {
  it('播放位置居中 → 视口 [t-7.5, t+7.5], 竖线在中央', () => {
    const r = computeScrollWindow({
      viewportSeconds: 15,
      totalDuration: 60,
      currentTime: 20,
    })
    expect(r.windowStart).toBeCloseTo(12.5)
    expect(r.windowEnd).toBeCloseTo(27.5)
    expect(r.cursorXFraction).toBeCloseTo(0.5)
  })

  it('开头 → 视口从 0 开始, 竖线靠左', () => {
    const r = computeScrollWindow({
      viewportSeconds: 15,
      totalDuration: 60,
      currentTime: 0,
    })
    expect(r.windowStart).toBe(0)
    expect(r.windowEnd).toBeCloseTo(15)
    expect(r.cursorXFraction).toBeCloseTo(0)
  })

  it('结尾 → 视口贴尾, 竖线靠右', () => {
    const r = computeScrollWindow({
      viewportSeconds: 15,
      totalDuration: 60,
      currentTime: 60,
    })
    expect(r.windowStart).toBeCloseTo(45)
    expect(r.windowEnd).toBeCloseTo(60)
    expect(r.cursorXFraction).toBeCloseTo(1)
  })

  it('视口大于总时长 → 全曲可见', () => {
    const r = computeScrollWindow({
      viewportSeconds: 15,
      totalDuration: 5,
      currentTime: 2,
    })
    expect(r.windowStart).toBe(0)
    expect(r.windowEnd).toBeCloseTo(5)
    expect(r.cursorXFraction).toBeCloseTo(0.4)
  })

  it('游标时间越界 → 钳制到有效范围', () => {
    const r = computeScrollWindow({
      viewportSeconds: 15,
      totalDuration: 30,
      currentTime: 100, // 越界
    })
    expect(r.windowEnd).toBeCloseTo(30)
    expect(r.cursorXFraction).toBe(1)
  })
})

describe('cursorXFraction', () => {
  it('与 computeScrollWindow 一致 (独立实现)', () => {
    expect(cursorXFraction(20, 12.5, 27.5)).toBeCloseTo(0.5)
  })

  it('窗口外 → 钳制 0..1', () => {
    expect(cursorXFraction(0, 10, 20)).toBe(0)
    expect(cursorXFraction(30, 10, 20)).toBe(1)
  })
})

describe('trimSilence', () => {
  it('裁剪首尾无声帧', () => {
    const frames: PitchPoint[] = [
      { time: 0.0, frequency: 0, confidence: 0.1 },
      { time: 0.5, frequency: 0, confidence: 0.1 },
      { time: 1.0, frequency: 440, confidence: 1 },
      { time: 1.5, frequency: 440, confidence: 1 },
      { time: 2.0, frequency: 0, confidence: 0.1 },
    ]
    const { startIdx, endIdx } = trimSilence(frames)
    expect(startIdx).toBe(2)
    expect(endIdx).toBe(3)
  })

  it('全静音 → 返回空区间', () => {
    const frames: PitchPoint[] = [
      { time: 0.0, frequency: 0, confidence: 0.1 },
      { time: 0.5, frequency: 0, confidence: 0.1 },
    ]
    const { startIdx, endIdx } = trimSilence(frames)
    expect(startIdx).toBe(0)
    expect(endIdx).toBe(-1)
  })
})

describe('autoViewportSeconds', () => {
  it('短音频 (≤10s) → 全曲', () => {
    expect(autoViewportSeconds(5)).toBeCloseTo(5)
    expect(autoViewportSeconds(10)).toBeCloseTo(10)
  })

  it('长音频 → 15s 视口', () => {
    expect(autoViewportSeconds(30)).toBe(15)
    expect(autoViewportSeconds(180)).toBe(15)
  })
})
