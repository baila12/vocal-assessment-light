/**
 * pitchSegments 单元测试 — v7.13 Phase 4 录音后回放分析
 *
 * 纯函数: 问题段落检测 / 乐句切分 / 逐句音准评分。
 * 对齐 pitch-realtime.feature 第五节 Scenario "选歌录音 — 录音后回放对比":
 *   - 问题段落应用红色半透明背景高亮 (偏差 > 50 音分持续 > 0.5s)
 *   - 应显示逐句音准评分 (每句一个分数标签浮在曲线上方)
 */
import { describe, it, expect } from 'vitest'
import { findProblemSegments, segmentPhrases, scorePhrase, phraseScoreColor } from '@/utils/pitchSegments'
import type { DeviationFrame, PitchPoint } from '@/types/pitch'

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

/** 生成 time 从 start 起、间隔 step 的连续帧序列 */
function run(start: number, count: number, step = 0.1, over: Partial<DeviationFrame> = {}): DeviationFrame[] {
  return Array.from({ length: count }, (_, i) => frame({ time: start + i * step, ...over }))
}

function refPoint(time: number, frequency = 440): PitchPoint {
  return { time, frequency, confidence: 1 }
}

describe('findProblemSegments', () => {
  it('空数组 → []', () => {
    expect(findProblemSegments([])).toEqual([])
  })

  it('全部无声 → []', () => {
    const frames = run(0, 10, 0.1, { isSilent: true, colorHex: '#94a3b8' })
    expect(findProblemSegments(frames)).toEqual([])
  })

  it('全部精准 (无问题帧) → []', () => {
    const frames = run(0, 10, 0.1, { absCentsDeviation: 10 })
    expect(findProblemSegments(frames)).toEqual([])
  })

  it('单帧问题 (未持续 0.5s) → []', () => {
    const frames = [frame({ time: 0, absCentsDeviation: 60 })]
    expect(findProblemSegments(frames)).toEqual([])
  })

  it('连续问题帧持续 ≥0.5s → 一个段落 [首, 尾]', () => {
    // t=0..0.5 (6 帧, 首尾跨度 0.5s ≥ 0.5)
    const frames = run(0, 6, 0.1, { absCentsDeviation: 60 })
    expect(findProblemSegments(frames)).toEqual([{ start: 0, end: 0.5 }])
  })

  it('问题段被无声帧打断 → 两段 (各段均 ≥0.5s)', () => {
    const problem = { absCentsDeviation: 60 }
    const frames = [
      ...run(0, 6, 0.1, problem), // 0..0.5
      frame({ time: 0.6, isSilent: true, colorHex: '#94a3b8' }),
      ...run(0.7, 6, 0.1, problem), // 0.7..1.2
    ]
    expect(findProblemSegments(frames)).toEqual([
      { start: 0, end: 0.5 },
      { start: 0.7, end: 1.2 },
    ])
  })

  it('问题段被精准帧打断 → 两段 (各段均 ≥0.5s)', () => {
    const frames = [
      ...run(0, 6, 0.1, { absCentsDeviation: 60 }), // 0..0.5
      frame({ time: 0.6, absCentsDeviation: 10 }),
      ...run(0.7, 6, 0.1, { absCentsDeviation: 60 }), // 0.7..1.2
    ]
    expect(findProblemSegments(frames)).toEqual([
      { start: 0, end: 0.5 },
      { start: 0.7, end: 1.2 },
    ])
  })

  it('八度跳变帧不计为问题 (可能误检) — 且打断问题段', () => {
    const frames = [
      ...run(0, 6, 0.1, { absCentsDeviation: 60 }), // 0..0.5
      frame({ time: 0.6, absCentsDeviation: 80, isOctaveJump: true, colorHex: '#94a3b8' }),
      ...run(0.7, 6, 0.1, { absCentsDeviation: 60 }), // 0.7..1.2
    ]
    expect(findProblemSegments(frames)).toEqual([
      { start: 0, end: 0.5 },
      { start: 0.7, end: 1.2 },
    ])
  })

  it('|偏差| 恰好等于阈值 → 不算问题 (> 阈值才计)', () => {
    const frames = run(0, 6, 0.1, { absCentsDeviation: 50 })
    expect(findProblemSegments(frames)).toEqual([])
  })

  it('自定义阈值与最短时长', () => {
    // 阈值 30: 偏差 40 也算问题; 时长 1.0: 0..0.5 不足 → []
    const frames = run(0, 6, 0.1, { absCentsDeviation: 40 })
    expect(findProblemSegments(frames, 30, 1.0)).toEqual([])
    // 0..1.0 (11 帧, 跨度 1.0 ≥ 1.0) → 命中
    const long = run(0, 11, 0.1, { absCentsDeviation: 40 })
    expect(findProblemSegments(long, 30, 1.0)).toEqual([{ start: 0, end: 1 }])
  })

  it('问题帧位于数据开头与结尾', () => {
    const frames = [
      ...run(0, 6, 0.1, { absCentsDeviation: 60 }), // 0..0.5
      ...run(0.6, 4, 0.1, { absCentsDeviation: 10 }),
      ...run(1.0, 6, 0.1, { absCentsDeviation: 60 }), // 1.0..1.5
    ]
    expect(findProblemSegments(frames)).toEqual([
      { start: 0, end: 0.5 },
      { start: 1.0, end: 1.5 },
    ])
  })
})

describe('segmentPhrases', () => {
  it('空数组 → []', () => {
    expect(segmentPhrases([])).toEqual([])
  })

  it('无有效帧 (全静音/全零频) → []', () => {
    expect(segmentPhrases([refPoint(0, 0), refPoint(1, 0)])).toEqual([])
  })

  it('连续无间隙 → 单个乐句 [首, 尾]', () => {
    const pts = [refPoint(0), refPoint(0.1), refPoint(0.2)]
    expect(segmentPhrases(pts)).toEqual([{ start: 0, end: 0.2 }])
  })

  it('静音间隙 > 阈值 → 拆成两乐句', () => {
    // 0..0.2, 间隙 1.0 (0.3→1.3), 1.3..1.5
    const pts = [refPoint(0), refPoint(0.2), refPoint(1.3), refPoint(1.5)]
    expect(segmentPhrases(pts)).toEqual([
      { start: 0, end: 0.2 },
      { start: 1.3, end: 1.5 },
    ])
  })

  it('间隙恰好等于阈值 → 不拆 (> 阈值才拆)', () => {
    const pts = [refPoint(0), refPoint(0.4)] // 间隙 0.4 == minGap
    expect(segmentPhrases(pts)).toEqual([{ start: 0, end: 0.4 }])
  })

  it('自定义间隙阈值', () => {
    const pts = [refPoint(0), refPoint(0.3), refPoint(0.9)] // 间隙 0.6
    expect(segmentPhrases(pts, 0.5)).toEqual([
      { start: 0, end: 0.3 },
      { start: 0.9, end: 0.9 },
    ])
    expect(segmentPhrases(pts, 1.0)).toEqual([{ start: 0, end: 0.9 }])
  })

  it('乱序输入 → 按时间排序切分', () => {
    const pts = [refPoint(1.5), refPoint(0.2), refPoint(0), refPoint(1.3)]
    expect(segmentPhrases(pts)).toEqual([
      { start: 0, end: 0.2 },
      { start: 1.3, end: 1.5 },
    ])
  })

  it('首尾静音裁剪 — 乐句边界为有效帧时间', () => {
    const pts = [refPoint(0, 0), refPoint(0.1), refPoint(0.5), refPoint(2.0, 0)]
    expect(segmentPhrases(pts)).toEqual([{ start: 0.1, end: 0.5 }])
  })
})

describe('scorePhrase', () => {
  it('空数组 → null', () => {
    expect(scorePhrase([], 0, 10)).toBeNull()
  })

  it('句内全部精准 → 100', () => {
    const frames = run(0, 5, 0.1, { absCentsDeviation: 10 })
    expect(scorePhrase(frames, 0, 1)).toBe(100)
  })

  it('句内全部跑调 → 0', () => {
    const frames = run(0, 5, 0.1, { absCentsDeviation: 60 })
    expect(scorePhrase(frames, 0, 1)).toBe(0)
  })

  it('混合 → 精准帧占比', () => {
    const frames = [
      frame({ time: 0, absCentsDeviation: 10 }),
      frame({ time: 0.1, absCentsDeviation: 60 }),
      frame({ time: 0.2, absCentsDeviation: 10 }),
      frame({ time: 0.3, absCentsDeviation: 10 }),
    ] // 精准 3/4 = 75
    expect(scorePhrase(frames, 0, 1)).toBe(75)
  })

  it('区间外帧排除 (仅 [start, end] 内计入)', () => {
    const frames = [
      frame({ time: -1, absCentsDeviation: 60 }),
      frame({ time: 0.5, absCentsDeviation: 10 }),
      frame({ time: 2, absCentsDeviation: 60 }),
    ]
    expect(scorePhrase(frames, 0, 1)).toBe(100)
  })

  it('边界帧包含 (≥ start 且 ≤ end)', () => {
    const frames = [
      frame({ time: 0, absCentsDeviation: 60 }),
      frame({ time: 1, absCentsDeviation: 10 }),
    ]
    expect(scorePhrase(frames, 0, 1)).toBe(50)
  })

  it('句内全无声 → null', () => {
    const frames = run(0, 5, 0.1, { isSilent: true, colorHex: '#94a3b8' })
    expect(scorePhrase(frames, 0, 1)).toBeNull()
  })

  it('无声帧排除在分母外', () => {
    const frames = [
      frame({ time: 0, absCentsDeviation: 10 }),
      frame({ time: 0.1, isSilent: true, colorHex: '#94a3b8' }),
      frame({ time: 0.2, absCentsDeviation: 60 }),
    ] // 有效 2 帧, 精准 1/2 = 50
    expect(scorePhrase(frames, 0, 1)).toBe(50)
  })

  it('自定义精准阈值', () => {
    const frames = run(0, 4, 0.1, { absCentsDeviation: 40 })
    // 阈值 25 → 全部略偏 → 0; 阈值 50 → 全部精准 → 100
    expect(scorePhrase(frames, 0, 1, 25)).toBe(0)
    expect(scorePhrase(frames, 0, 1, 50)).toBe(100)
  })

  it('分数取整 (四舍五入)', () => {
    const frames = [
      frame({ time: 0, absCentsDeviation: 10 }),
      frame({ time: 0.1, absCentsDeviation: 60 }),
      frame({ time: 0.2, absCentsDeviation: 60 }),
    ] // 精准 1/3 = 33.33 → 33
    expect(scorePhrase(frames, 0, 1)).toBe(33)
  })
})

describe('phraseScoreColor', () => {
  it('≥85 → 绿 (精准句)', () => {
    expect(phraseScoreColor(100)).toBe('#22c55e')
    expect(phraseScoreColor(90)).toBe('#22c55e')
    expect(phraseScoreColor(85)).toBe('#22c55e') // 边界含
  })

  it('60-84 → 橙 (略偏句)', () => {
    expect(phraseScoreColor(84)).toBe('#f59e0b')
    expect(phraseScoreColor(60)).toBe('#f59e0b') // 边界含
  })

  it('<60 → 红 (跑调句)', () => {
    expect(phraseScoreColor(59)).toBe('#ef4444')
    expect(phraseScoreColor(0)).toBe('#ef4444')
  })
})
