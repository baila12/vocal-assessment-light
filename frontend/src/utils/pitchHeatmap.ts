/**
 * 偏差热力图计算 — v7.13 Phase 5 对比分析双轨叠加
 *
 * 纯函数, 零 Vue 依赖, 可直接 Vitest 测试。
 * 对齐 pitch-realtime.feature:
 *   - "底部应显示偏差热力图条 (一整行, 颜色密度表示跑调程度)"
 *   - "点击偏差热力图任意位置可跳转播放"
 *   - 低对齐段内的桶置灰 (DTW 置信度 <0.5 不误导)
 * 颜色复用 deviationColor (≤25 绿 / 25-50 橙 / >50 红) 保持系统一致。
 */
import { DEVIATION_COLORS, deviationColor } from '@/utils/pitchDeviation'
import type { DeviationFrame, LowAlignmentSegment } from '@/types/pitch'

/** 热力图桶段 */
export interface HeatmapSegment {
  /** 段起点 (秒) */
  readonly startTime: number
  /** 段终点 (秒) */
  readonly endTime: number
  /** 桶内有声帧的平均绝对音分偏差 (无声帧不计入) */
  readonly severity: number
  /** 桶内跑调帧占比 (absCentsDeviation > 50) — 0-1, 无有效帧为 0 */
  readonly outOfTuneFraction: number
  /** 渲染颜色 — deviationColor(平均偏差); 落在低对齐段内 → 灰 */
  readonly color: string
}

/** 桶区间是否与任一低对齐段相交 */
function intersectsLowAlignment(
  startTime: number,
  endTime: number,
  segments: readonly LowAlignmentSegment[],
): boolean {
  for (const seg of segments) {
    if (seg.end <= startTime || seg.start >= endTime) continue
    return true
  }
  return false
}

/**
 * 把帧划分为 numBuckets 个等宽时间桶, 统计偏差严重度。
 * 空帧 / totalDuration<=0 → []; numBuckets<1 → 钳制为 1。
 */
export function computeHeatmapSegments(
  frames: readonly DeviationFrame[],
  totalDuration: number,
  numBuckets: number,
  lowAlignmentSegments: readonly LowAlignmentSegment[] = [],
): readonly HeatmapSegment[] {
  if (frames.length === 0 || totalDuration <= 0) return []
  const buckets = Math.max(1, numBuckets)
  const bucketWidth = totalDuration / buckets

  const severitySum = new Array<number>(buckets).fill(0)
  const outOfTuneCount = new Array<number>(buckets).fill(0)
  const voicedCount = new Array<number>(buckets).fill(0)

  for (const f of frames) {
    if (f.isSilent || f.frequency <= 0) continue
    const idx = Math.min(buckets - 1, Math.max(0, Math.floor(f.time / bucketWidth)))
    severitySum[idx] += f.absCentsDeviation
    voicedCount[idx]++
    if (f.absCentsDeviation > 50) outOfTuneCount[idx]++
  }

  const segments: HeatmapSegment[] = []
  for (let i = 0; i < buckets; i++) {
    const startTime = i * bucketWidth
    const endTime = i === buckets - 1 ? totalDuration : (i + 1) * bucketWidth
    const voiced = voicedCount[i]
    const severity = voiced > 0 ? severitySum[i] / voiced : 0
    const isLowAlignment = intersectsLowAlignment(startTime, endTime, lowAlignmentSegments)

    segments.push({
      startTime,
      endTime,
      severity,
      outOfTuneFraction: voiced > 0 ? outOfTuneCount[i] / voiced : 0,
      // 空桶 (无有效帧) 或落在低对齐段内 → 灰; 否则按偏差着色
      color:
        voiced === 0 || isLowAlignment ? DEVIATION_COLORS.silent : deviationColor(severity),
    })
  }
  return segments
}

/**
 * 热力图点击 → 时间。xRatio ∈ [0,1] 钳制后映射到 [0, totalDuration]。
 * totalDuration<=0 → 0。
 */
export function heatmapClickToTime(xRatio: number, totalDuration: number): number {
  if (totalDuration <= 0) return 0
  const clamped = Math.max(0, Math.min(1, xRatio))
  return clamped * totalDuration
}
