/**
 * pitchScroll 时间刻度扩展测试 — v7.13 Phase 2 X 轴
 *
 * 纯函数: 自动刻度步长 / 时间刻度生成。
 * 对齐 pitch-realtime.feature:
 *   - 短音频: "时间轴刻度应调整为秒级精度 (每格 1 秒)"
 *   - 长音频: "可见范围约 15 秒" + "底部应有缩略导航条"
 */
import { describe, it, expect } from 'vitest'
import { autoTickStepSeconds, generateTimeTicks } from '@/utils/pitchScroll'

describe('autoTickStepSeconds', () => {
  it('短音频 (≤10s) → 1 秒/格', () => {
    expect(autoTickStepSeconds(5)).toBe(1)
    expect(autoTickStepSeconds(10)).toBe(1)
  })

  it('中等音频 (≤60s) → 5 秒/格', () => {
    expect(autoTickStepSeconds(30)).toBe(5)
    expect(autoTickStepSeconds(60)).toBe(5)
  })

  it('长音频 (>60s) → 15 秒/格', () => {
    expect(autoTickStepSeconds(180)).toBe(15)
    expect(autoTickStepSeconds(240)).toBe(15)
  })

  it('非正时长 → 1 秒/格 (兜底)', () => {
    expect(autoTickStepSeconds(0)).toBe(1)
    expect(autoTickStepSeconds(-1)).toBe(1)
  })
})

describe('generateTimeTicks', () => {
  it('0-5s 步长 1 → [0,1,2,3,4,5] (含端点)', () => {
    expect(generateTimeTicks(5, 1)).toEqual([0, 1, 2, 3, 4, 5])
  })

  it('0-30s 步长 5 → [0,5,10,15,20,25,30]', () => {
    expect(generateTimeTicks(30, 5)).toEqual([0, 5, 10, 15, 20, 25, 30])
  })

  it('端点不是步长倍数 → 不含尾部非整步 (不超范围)', () => {
    // 0..14 步长 5 → 0,5,10 (14 不是 5 的倍数)
    expect(generateTimeTicks(14, 5)).toEqual([0, 5, 10])
  })

  it('非正步长 → 空数组', () => {
    expect(generateTimeTicks(10, 0)).toEqual([])
    expect(generateTimeTicks(10, -1)).toEqual([])
  })

  it('非正时长 → 空数组', () => {
    expect(generateTimeTicks(0, 1)).toEqual([])
  })
})
