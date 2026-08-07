/**
 * 音高刻度工具 — v7.13 Phase 2 音准对比视图 Y 轴
 *
 * 纯函数, 零 Vue 依赖, 可直接 Vitest 测试。
 * 对齐 pitch-realtime.feature: "Y 轴标注音高 (C3-B5, 钢琴键白键高亮)"。
 * 使用科学音高记法: C4 = MIDI 60 = 261.63Hz, A4 = 440Hz = MIDI 69。
 */
import type { PitchPoint } from '@/types/pitch'

/** A4 频率 (Hz) — 音高定标基准 */
export const A4_FREQUENCY = 440
/** A4 的 MIDI 编号 */
export const A4_MIDI = 69
/** 每八度半音数 */
export const SEMITONES_PER_OCTAVE = 12

const NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
/** 白键的半音偏移 (0-11) */
const WHITE_KEY_OFFSETS = new Set([0, 2, 4, 5, 7, 9, 11])

/** 频率 (Hz) → 最近 MIDI 编号; 非正频率 → 0 */
export function freqToMidi(freq: number): number {
  if (freq <= 0 || !Number.isFinite(freq)) return 0
  return Math.round(A4_MIDI + SEMITONES_PER_OCTAVE * Math.log2(freq / A4_FREQUENCY))
}

/** MIDI 编号 → 科学音高记法音名 (如 60 → 'C4') */
export function midiToNoteName(midi: number): string {
  const safe = Math.max(0, Math.min(127, Math.round(midi)))
  const pitchClass = NOTE_NAMES[safe % SEMITONES_PER_OCTAVE]
  const octave = Math.floor(safe / SEMITONES_PER_OCTAVE) - 1
  return `${pitchClass}${octave}`
}

/** 频率 (Hz) → 音名 (如 440 → 'A4'); 非正频率 → null */
export function freqToNoteName(freq: number): string | null {
  const midi = freqToMidi(freq)
  if (midi <= 0) return null
  return midiToNoteName(midi)
}

/** MIDI 编号是否白键 (钢琴键高亮) */
export function isWhiteKey(midi: number): boolean {
  return WHITE_KEY_OFFSETS.has(Math.round(midi) % SEMITONES_PER_OCTAVE)
}

export interface NoteTick {
  midi: number
  name: string
  isWhite: boolean
}

/** 生成 [minMidi, maxMidi] 闭区间内的半音刻度 (供 Y 轴标注) */
export function generateNoteTicks(minMidi: number, maxMidi: number): NoteTick[] {
  // 倒置范围 → 空 (调用方需保证 min <= max)
  if (minMidi > maxMidi) return []
  const from = Math.ceil(minMidi)
  const to = Math.floor(maxMidi)
  if (from > to) return []

  const ticks: NoteTick[] = []
  for (let midi = from; midi <= to; midi++) {
    ticks.push({ midi, name: midiToNoteName(midi), isWhite: isWhiteKey(midi) })
  }
  return ticks
}

/** 一组音高点 → [minMidi, maxMidi] (仅有效帧); 无有效帧 → null */
export function pitchRangeToMidi(points: PitchPoint[]): { minMidi: number; maxMidi: number } | null {
  let minMidi = Infinity
  let maxMidi = -Infinity
  for (const p of points) {
    if (p.frequency <= 0) continue
    const midi = freqToMidi(p.frequency)
    if (midi < minMidi) minMidi = midi
    if (midi > maxMidi) maxMidi = midi
  }
  if (!Number.isFinite(minMidi)) return null
  return { minMidi, maxMidi }
}
