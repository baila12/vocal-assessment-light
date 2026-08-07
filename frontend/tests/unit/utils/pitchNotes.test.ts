/**
 * pitchNotes 单元测试 — v7.13 Phase 2 音高刻度
 *
 * 纯函数: 频率→MIDI / MIDI→音名 / 白键判定 / 音高刻度生成。
 * 对齐 pitch-realtime.feature "Y 轴标注音高 (C3-B5, 钢琴键白键高亮)"。
 */
import { describe, it, expect } from 'vitest'
import {
  freqToMidi,
  midiToNoteName,
  freqToNoteName,
  isWhiteKey,
  generateNoteTicks,
} from '@/utils/pitchNotes'

describe('freqToMidi', () => {
  it('A4 = 440Hz → MIDI 69', () => {
    expect(freqToMidi(440)).toBe(69)
  })

  it('A4 低一个八度 (220Hz) → MIDI 57', () => {
    expect(freqToMidi(220)).toBe(57)
  })

  it('A4 高一个八度 (880Hz) → MIDI 81', () => {
    expect(freqToMidi(880)).toBe(81)
  })

  it('C4 = 261.63Hz → MIDI 60', () => {
    expect(freqToMidi(261.63)).toBe(60)
  })

  it('非正频率 (无声) → 0', () => {
    expect(freqToMidi(0)).toBe(0)
    expect(freqToMidi(-1)).toBe(0)
  })

  it('就近取整 — 轻微失谐仍映射到最近半音', () => {
    expect(freqToMidi(440.5)).toBe(69)
  })
})

describe('midiToNoteName', () => {
  it('MIDI 60 → C4', () => {
    expect(midiToNoteName(60)).toBe('C4')
  })

  it('MIDI 69 → A4', () => {
    expect(midiToNoteName(69)).toBe('A4')
  })

  it('MIDI 48 → C3 (B5 上方两个八度)', () => {
    expect(midiToNoteName(48)).toBe('C3')
  })

  it('MIDI 83 → B5', () => {
    expect(midiToNoteName(83)).toBe('B5')
  })

  it('黑键 — MIDI 61 → C#4', () => {
    expect(midiToNoteName(61)).toBe('C#4')
  })

  it('黑键 — MIDI 70 → A#4', () => {
    expect(midiToNoteName(70)).toBe('A#4')
  })
})

describe('freqToNoteName', () => {
  it('440Hz → A4', () => {
    expect(freqToNoteName(440)).toBe('A4')
  })

  it('261.63Hz → C4', () => {
    expect(freqToNoteName(261.63)).toBe('C4')
  })

  it('非正频率 → null (无声/未检出)', () => {
    expect(freqToNoteName(0)).toBeNull()
  })
})

describe('isWhiteKey', () => {
  it('C (0), D (2), E (4), F (5), G (7), A (9), B (11) 为白键', () => {
    expect(isWhiteKey(0)).toBe(true)
    expect(isWhiteKey(2)).toBe(true)
    expect(isWhiteKey(4)).toBe(true)
    expect(isWhiteKey(5)).toBe(true)
    expect(isWhiteKey(7)).toBe(true)
    expect(isWhiteKey(9)).toBe(true)
    expect(isWhiteKey(11)).toBe(true)
  })

  it('C# (1), D# (3), F# (6), G# (8), A# (10) 为黑键', () => {
    expect(isWhiteKey(1)).toBe(false)
    expect(isWhiteKey(3)).toBe(false)
    expect(isWhiteKey(6)).toBe(false)
    expect(isWhiteKey(8)).toBe(false)
    expect(isWhiteKey(10)).toBe(false)
  })

  it('跨八度 — 60 (C4) 白键, 61 (C#4) 黑键', () => {
    expect(isWhiteKey(60)).toBe(true)
    expect(isWhiteKey(61)).toBe(false)
  })
})

describe('generateNoteTicks', () => {
  it('C3-B5 → 每半音一个刻度, 标注白键音名', () => {
    const ticks = generateNoteTicks(48, 83)
    // 36 个半音 (48..83 含端点) → 36 个刻度
    expect(ticks).toHaveLength(36)
    expect(ticks[0]).toMatchObject({ midi: 48, name: 'C3', isWhite: true })
    expect(ticks[35]).toMatchObject({ midi: 83, name: 'B5', isWhite: true })
  })

  it('黑键刻度 isWhite=false 且带 #', () => {
    const ticks = generateNoteTicks(60, 61)
    expect(ticks).toHaveLength(2)
    expect(ticks[1]).toMatchObject({ midi: 61, name: 'C#4', isWhite: false })
  })

  it('范围倒置 → 返回空数组', () => {
    expect(generateNoteTicks(60, 48)).toHaveLength(0)
  })

  it('单点 → 一个刻度', () => {
    const ticks = generateNoteTicks(69, 69)
    expect(ticks).toHaveLength(1)
    expect(ticks[0].name).toBe('A4')
  })
})
