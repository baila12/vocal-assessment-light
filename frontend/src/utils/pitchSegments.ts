/**
 * 录音后回放分析 — v7.13 Phase 4
 *
 * 纯函数, 零 Vue 依赖, 可直接 Vitest 测试。
 * 对齐 pitch-realtime.feature 第五节 Scenario "选歌录音 — 录音后回放对比":
 *   - 问题段落: 偏差 > 50 音分持续 > 0.5s → 红色半透明背景高亮 (findProblemSegments)
 *   - 逐句音准评分: 参考曲线静音间隙切分乐句, 每句一个分数标签 (segmentPhrases + scorePhrase)
 */
import { DEVIATION_THRESHOLDS } from '@/utils/pitchDeviation'
import type { DeviationFrame, PitchPoint } from '@/types/pitch'

/** 时间区间 — 问题段落 / 乐句 */
export interface TimeRange {
  start: number
  end: number
}

/**
 * 问题段落检测 — 连续有声非八度跳变帧 |偏差| > 阈值 (默认 50 音分) 且跨度 ≥ 最短时长 (默认 0.5s)。
 * 静音 (检测不到 ≠ 跑调) 与八度跳变 (可能误检) 不计入并打断问题段。
 */
export function findProblemSegments(
  frames: DeviationFrame[],
  thresholdCents: number = DEVIATION_THRESHOLDS.slightBias,
  minDurationSeconds: number = 0.5,
): TimeRange[] {
  const segments: TimeRange[] = []
  let runStart = -1
  let lastTime = 0

  for (const f of frames) {
    const isProblem = !f.isSilent && !f.isOctaveJump && f.absCentsDeviation > thresholdCents
    if (isProblem) {
      if (runStart < 0) runStart = f.time
      lastTime = f.time
      continue
    }
    // 非问题帧 → 闭合当前段
    if (runStart >= 0) {
      if (lastTime - runStart >= minDurationSeconds) {
        segments.push({ start: runStart, end: lastTime })
      }
      runStart = -1
    }
  }
  // 末尾未闭合的段
  if (runStart >= 0 && lastTime - runStart >= minDurationSeconds) {
    segments.push({ start: runStart, end: lastTime })
  }
  return segments
}

/**
 * 乐句切分 — 参考曲线有效帧 (frequency > 0) 按静音间隙 (> minGap 默认 0.4s) 分组。
 * 返回每句有效帧的首尾时间; 无有效帧 → []。
 */
export function segmentPhrases(
  refPitchData: PitchPoint[],
  minGapSeconds: number = 0.4,
): TimeRange[] {
  const voiced = refPitchData
    .filter((p) => p.frequency > 0)
    .sort((a, b) => a.time - b.time)
  if (voiced.length === 0) return []

  const phrases: TimeRange[] = []
  let phraseStart = voiced[0].time
  let prevTime = voiced[0].time

  for (let i = 1; i < voiced.length; i++) {
    const t = voiced[i].time
    if (t - prevTime > minGapSeconds) {
      phrases.push({ start: phraseStart, end: prevTime })
      phraseStart = t
    }
    prevTime = t
  }
  phrases.push({ start: phraseStart, end: prevTime })
  return phrases
}

/**
 * 逐句音准评分 — 句内有效帧的精准率 (|偏差| ≤ 阈值默认 25 音分), 无声帧排除。
 * 返回 0-100 整数; 句内无有效帧 → null。
 */
export function scorePhrase(
  frames: DeviationFrame[],
  start: number,
  end: number,
  accurateThresholdCents: number = DEVIATION_THRESHOLDS.accurate,
): number | null {
  let voiced = 0
  let accurate = 0

  for (const f of frames) {
    if (f.time < start || f.time > end) continue
    if (f.isSilent) continue
    voiced++
    if (f.absCentsDeviation <= accurateThresholdCents) accurate++
  }

  if (voiced === 0) return null
  return Math.round((accurate / voiced) * 100)
}

/** 逐句评分标签颜色 — ≥85 绿 / 60-84 橙 / <60 红 (与偏差三色一致) */
export function phraseScoreColor(score: number): string {
  if (score >= 85) return '#22c55e'
  if (score >= 60) return '#f59e0b'
  return '#ef4444'
}
