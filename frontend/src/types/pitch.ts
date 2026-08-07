/**
 * 音准对比类型 — v7.13 实时音准对比子系统
 *
 * 共享类型: 音高数据点 / 偏差帧 / 统计。
 */

/** 音高数据点 — 单帧 */
export interface PitchPoint {
  /** 时间 (秒, 相对录音/音频起点) */
  time: number
  /** 频率 (Hz), 0 = 无声/未检出 */
  frequency: number
  /** 置信度 (0-1) */
  confidence: number
}

/** 偏差帧 — alignPitchCurves 的输出 */
export interface DeviationFrame extends PitchPoint {
  /** 对齐后的参考频率 (Hz, 线性插值) */
  refFrequency: number
  /** 音分偏差 (正=偏高, 负=偏低) */
  centsDeviation: number
  /** 绝对音分偏差 */
  absCentsDeviation: number
  /** 渲染颜色 (偏差着色/灰) */
  colorHex: string
  /** 无声段 */
  isSilent: boolean
  /** 八度跳变 (可能误检) */
  isOctaveJump: boolean
}

/** 低对齐段落 — DTW 置信度 <0.5 的区间 (v7.13 Phase 5) */
export interface LowAlignmentSegment {
  /** 段起点 (秒) */
  start: number
  /** 段终点 (秒) */
  end: number
  /** 该段平均 DTW 置信度 (0-1) */
  avgConfidence: number
}
