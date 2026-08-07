/**
 * pitchPlayback 单元测试 — v7.13 Phase 2 播放控制
 *
 * 纯函数: 播放状态推进 / 倍速 / A-B 循环 / 拖拽钳制 / 渲染降级。
 * 对齐 pitch-realtime.feature 第三章 (播放控制):
 *   - "暂停时冻结曲线"
 *   - "拖拽进度条跳转" (200ms 内, 无重播动画)
 *   - "倍速播放 (0.5x / 1.5x)" — 滚动同步缩放, 刻度真实时间
 *   - "循环播放某一段落" — A-B 循环无缝
 *   - "渲染帧率保障" — 连续低帧率降级
 */
import { describe, it, expect } from 'vitest'
import {
  clampSeek,
  advancePlayback,
  PLAYBACK_RATES,
  DEFAULT_PLAYBACK_RATE,
  isInABLoop,
  wrapInABLoop,
  shouldDegradeFrameRate,
} from '@/utils/pitchPlayback'

describe('clampSeek', () => {
  it('范围内 → 原值', () => {
    expect(clampSeek(30, 120)).toBe(30)
  })

  it('越界 (负数) → 钳制 0', () => {
    expect(clampSeek(-5, 120)).toBe(0)
  })

  it('越界 (超时长) → 钳制到总时长', () => {
    expect(clampSeek(200, 120)).toBe(120)
  })

  it('非正时长 → 0', () => {
    expect(clampSeek(30, 0)).toBe(0)
    expect(clampSeek(30, -1)).toBe(0)
  })
})

describe('advancePlayback', () => {
  it('正常 1x → current + dt', () => {
    expect(advancePlayback({ current: 10, dt: 0.1, rate: 1, duration: 60 })).toBeCloseTo(10.1)
  })

  it('0.5x → 推进减半', () => {
    expect(advancePlayback({ current: 10, dt: 0.1, rate: 0.5, duration: 60 })).toBeCloseTo(10.05)
  })

  it('1.5x → 推进加速', () => {
    expect(advancePlayback({ current: 10, dt: 0.1, rate: 1.5, duration: 60 })).toBeCloseTo(10.15)
  })

  it('暂停 (rate 0) → 不动 (冻结)', () => {
    expect(advancePlayback({ current: 10, dt: 0.1, rate: 0, duration: 60 })).toBeCloseTo(10)
  })

  it('超过总时长 → 钳制到末尾 (不循环)', () => {
    expect(advancePlayback({ current: 59.95, dt: 0.1, rate: 1, duration: 60 })).toBeCloseTo(60)
  })

  it('非正时长 → 0', () => {
    expect(advancePlayback({ current: 10, dt: 0.1, rate: 1, duration: 0 })).toBe(0)
  })
})

describe('PLAYBACK_RATES / DEFAULT_PLAYBACK_RATE', () => {
  it('支持 0.5x / 1x / 1.5x', () => {
    expect(PLAYBACK_RATES).toEqual([0.5, 1, 1.5])
  })

  it('默认 1x', () => {
    expect(DEFAULT_PLAYBACK_RATE).toBe(1)
  })
})

describe('isInABLoop / wrapInABLoop', () => {
  it('isInABLoop — 区间内 true, 区间外 false', () => {
    expect(isInABLoop(15, { a: 10, b: 30 })).toBe(true)
    expect(isInABLoop(10, { a: 10, b: 30 })).toBe(true)
    expect(isInABLoop(5, { a: 10, b: 30 })).toBe(false)
    expect(isInABLoop(31, { a: 10, b: 30 })).toBe(false)
  })

  it('无循环 → false', () => {
    expect(isInABLoop(15, null)).toBe(false)
  })

  it('wrapInABLoop — 越过 B 点回绕到 A (无缝循环)', () => {
    expect(wrapInABLoop(31, { a: 10, b: 30 })).toBeCloseTo(11)
  })

  it('wrapInABLoop — 在区间内不变', () => {
    expect(wrapInABLoop(15, { a: 10, b: 30 })).toBeCloseTo(15)
  })

  it('wrapInABLoop — 无循环/非法区间 → 原值', () => {
    expect(wrapInABLoop(15, null)).toBe(15)
    expect(wrapInABLoop(15, { a: 30, b: 10 })).toBe(15) // a > b 非法
  })
})

describe('shouldDegradeFrameRate', () => {
  it('连续 3 秒帧率 < 20 → 降级', () => {
    expect(shouldDegradeFrameRate(19.5, 3.2)).toBe(true)
  })

  it('帧率 ≥ 20 → 不降级', () => {
    expect(shouldDegradeFrameRate(30, 5)).toBe(false)
    expect(shouldDegradeFrameRate(20, 5)).toBe(false)
  })

  it('低帧率但时间不足 3 秒 → 不降级 (短暂抖动)', () => {
    expect(shouldDegradeFrameRate(15, 2)).toBe(false)
  })

  it('非正帧率 → 不降级 (无数据)', () => {
    expect(shouldDegradeFrameRate(0, 5)).toBe(false)
    expect(shouldDegradeFrameRate(-1, 5)).toBe(false)
  })
})
