/**
 * pitchLive 单元测试 — v7.13 Phase 3 录音中实时对比
 *
 * 纯函数: 趋势分类 / 偏差显示格式 / 最近偏差 / 圆点 2s 淡出 / 色带频率几何。
 * 对齐 pitch-realtime.feature 第五节 Scenario "选歌录音 — 录音中实时对比":
 *   - 用户实时音高点 (每个音符 3px 圆点)
 *   - 偏差背景色带 (标准线上下 25/50 音分 绿色/橙色区域)
 *   - 当前音分偏差数值 (右上角 "+15 音分")
 *   - 音高趋势箭头 (偏高 ↑ 红 / 偏低 ↓ 蓝 / 精准 ✓ 绿)
 *   - 圆点在 2 秒后淡出 (保留最近的音高轨迹)
 */
import { describe, it, expect } from 'vitest'
import {
  deviationTrend,
  trendDisplay,
  formatCentsDeviation,
  latestDeviationCents,
  visibleLivePoints,
  dotAlpha,
  freqAtCentsOffset,
  LIVE_DOT_KEEP_SECONDS,
} from '@/utils/pitchLive'
import type { PitchPoint, DeviationFrame } from '@/types/pitch'

function frame(over: Partial<DeviationFrame> = {}): DeviationFrame {
  return {
    time: 0,
    frequency: 440,
    confidence: 1,
    refFrequency: 440,
    centsDeviation: 0,
    absCentsDeviation: 0,
    colorHex: '#22c55e',
    isSilent: false,
    isOctaveJump: false,
    ...over,
  }
}

describe('deviationTrend', () => {
  it('> 25 音分 → high (偏高)', () => {
    expect(deviationTrend(30)).toBe('high')
    expect(deviationTrend(25.1)).toBe('high')
  })

  it('< -25 音分 → low (偏低)', () => {
    expect(deviationTrend(-30)).toBe('low')
    expect(deviationTrend(-25.1)).toBe('low')
  })

  it('|偏差| ≤ 25 → on (精准)', () => {
    expect(deviationTrend(25)).toBe('on')
    expect(deviationTrend(-25)).toBe('on')
    expect(deviationTrend(0)).toBe('on')
  })
})

describe('trendDisplay', () => {
  it('偏高 → ↑ 红', () => {
    expect(trendDisplay('high')).toEqual({ symbol: '↑', color: '#ef4444', label: '偏高' })
  })

  it('偏低 → ↓ 蓝', () => {
    expect(trendDisplay('low')).toEqual({ symbol: '↓', color: '#3b82f6', label: '偏低' })
  })

  it('精准 → ✓ 绿', () => {
    expect(trendDisplay('on')).toEqual({ symbol: '✓', color: '#22c55e', label: '精准' })
  })
})

describe('formatCentsDeviation', () => {
  it('正偏差 → "+N 音分"', () => {
    expect(formatCentsDeviation(15)).toBe('+15 音分')
    expect(formatCentsDeviation(15.4)).toBe('+15 音分')
  })

  it('负偏差 → "-N 音分"', () => {
    expect(formatCentsDeviation(-12)).toBe('-12 音分')
    expect(formatCentsDeviation(-12.6)).toBe('-13 音分')
  })

  it('零偏差 → "0 音分" (含负零四舍五入)', () => {
    expect(formatCentsDeviation(0)).toBe('0 音分')
    expect(formatCentsDeviation(-0.4)).toBe('0 音分')
  })

  it('NaN/Infinity → "-- 音分" (退化输入防御, 防 "-NaN 音分" 垃圾输出)', () => {
    expect(formatCentsDeviation(Number.NaN)).toBe('-- 音分')
    expect(formatCentsDeviation(Number.POSITIVE_INFINITY)).toBe('-- 音分')
    expect(formatCentsDeviation(Number.NEGATIVE_INFINITY)).toBe('-- 音分')
  })
})

describe('latestDeviationCents', () => {
  it('取最后一个有声帧的偏差', () => {
    const frames = [
      frame({ time: 0, centsDeviation: 10 }),
      frame({ time: 1, centsDeviation: -8 }),
    ]
    expect(latestDeviationCents(frames)).toBe(-8)
  })

  it('跳过末段静音帧 (无声时延续最近有效偏差)', () => {
    const frames = [
      frame({ time: 0, centsDeviation: 10 }),
      frame({ time: 1, centsDeviation: 20 }),
      frame({ time: 2, isSilent: true, colorHex: '#94a3b8' }),
    ]
    expect(latestDeviationCents(frames)).toBe(20)
  })

  it('全静音 → null (无法判定趋势)', () => {
    const frames = [
      frame({ isSilent: true, colorHex: '#94a3b8' }),
      frame({ isSilent: true, colorHex: '#94a3b8' }),
    ]
    expect(latestDeviationCents(frames)).toBeNull()
  })

  it('空数组 → null', () => {
    expect(latestDeviationCents([])).toBeNull()
  })
})

describe('visibleLivePoints', () => {
  const pts: PitchPoint[] = [
    { time: 0, frequency: 440, confidence: 1 },
    { time: 2, frequency: 440, confidence: 1 },
    { time: 4.5, frequency: 440, confidence: 1 },
    { time: 6, frequency: 440, confidence: 1 }, // 未来点 (尚未唱到)
  ]

  it('now=5, keep=2 → 仅保留 [3,5] 内, 排除未来点', () => {
    const vis = visibleLivePoints(pts, 5)
    expect(vis.map((p) => p.time)).toEqual([4.5])
  })

  it('now=6.2 → 保留 [4.2,6.2]', () => {
    const vis = visibleLivePoints(pts, 6.2)
    expect(vis.map((p) => p.time)).toEqual([4.5, 6])
  })

  it('自定义 keep 窗口 (如 5s)', () => {
    const vis = visibleLivePoints(pts, 5, 5)
    expect(vis.map((p) => p.time)).toEqual([0, 2, 4.5])
  })

  it('空数组 → 空', () => {
    expect(visibleLivePoints([], 5)).toEqual([])
  })

  it('keepSeconds ≤ 0 → 空 (提前返回分支覆盖)', () => {
    expect(visibleLivePoints(pts, 5, 0)).toEqual([])
    expect(visibleLivePoints(pts, 5, -1)).toEqual([])
  })
})

describe('dotAlpha', () => {
  it('age < 0 → 0 (未来点不可见)', () => {
    expect(dotAlpha(-1)).toBe(0)
  })

  it('未进入淡出阶段 → 1 (不透明)', () => {
    expect(dotAlpha(0)).toBe(1)
    expect(dotAlpha(1.4)).toBe(1) // keep=2, fade=0.5 → age ≤1.5 全不透明
  })

  it('进入淡出阶段 → 线性衰减', () => {
    expect(dotAlpha(1.7)).toBeCloseTo(0.6)
    expect(dotAlpha(1.9)).toBeCloseTo(0.2)
  })

  it('age ≥ keep → 0 (已淡出)', () => {
    expect(dotAlpha(2)).toBe(0)
    expect(dotAlpha(2.5)).toBe(0)
  })

  it('自定义 keep/fade 窗口', () => {
    expect(dotAlpha(4, 5, 1)).toBe(1) // remaining 1 ≥ fade 1 → 不透明
    expect(dotAlpha(4.5, 5, 1)).toBeCloseTo(0.5)
  })

  it('NaN/Infinity → 0 (退化输入防御, 防 NaN 透明度污染渲染)', () => {
    expect(dotAlpha(Number.NaN)).toBe(0)
    expect(dotAlpha(Number.POSITIVE_INFINITY)).toBe(0)
    expect(dotAlpha(Number.NEGATIVE_INFINITY)).toBe(0)
  })
})

describe('freqAtCentsOffset', () => {
  it('cents=0 → 原频率', () => {
    expect(freqAtCentsOffset(440, 0)).toBeCloseTo(440)
  })

  it('+25 音分 → 约 1.0145x (色带上缘)', () => {
    expect(freqAtCentsOffset(440, 25)).toBeCloseTo(440 * Math.pow(2, 25 / 1200))
  })

  it('-50 音分 → 约 0.9715x (色带下缘)', () => {
    expect(freqAtCentsOffset(440, -50)).toBeCloseTo(440 * Math.pow(2, -50 / 1200))
  })

  it('非正频率 → 0', () => {
    expect(freqAtCentsOffset(0, 25)).toBe(0)
    expect(freqAtCentsOffset(-1, 25)).toBe(0)
  })

  it('NaN/Infinity 频率或偏移 → 0 (退化输入防御)', () => {
    expect(freqAtCentsOffset(Number.NaN, 25)).toBe(0)
    expect(freqAtCentsOffset(440, Number.NaN)).toBe(0)
    expect(freqAtCentsOffset(Number.POSITIVE_INFINITY, 25)).toBe(0)
    expect(freqAtCentsOffset(440, Number.NEGATIVE_INFINITY)).toBe(0)
  })
})

describe('LIVE_DOT_KEEP_SECONDS', () => {
  it('圆点保留窗口 = 2s (feature: "圆点在 2 秒后淡出")', () => {
    expect(LIVE_DOT_KEEP_SECONDS).toBe(2)
  })
})
