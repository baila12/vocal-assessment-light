/**
 * 对比画布绘制助手 — v7.13 Phase 5 对比分析双轨叠加
 *
 * 纯 canvas 绘制函数 (无 Vue 依赖), 由 PitchComparisonCanvas 调用。
 * 对齐 pitch-realtime.feature:
 *   - 偏差热力图条: "底部应显示偏差热力图条 (一整行, 颜色密度表示跑调程度)"
 *   - DTW 未对齐段落: "灰色虚线 + ⚠️ 对齐不确定"
 *   - 缩略导航条: "全长预览 + 视口高亮 + 拖拽 seek"
 *   - 性能模式: "着色每 3 帧"
 */
import { DEFAULT_USER_COLOR, DEVIATION_COLORS, DEVIATION_THRESHOLDS } from '@/utils/pitchDeviation'
import {
  LIVE_DOT_KEEP_SECONDS,
  dotAlpha,
  formatCentsDeviation,
  freqAtCentsOffset,
  trendDisplay,
  type PitchTrend,
} from '@/utils/pitchLive'
import type { DeviationFrame, LowAlignmentSegment, PitchPoint } from '@/types/pitch'
import type { HeatmapSegment } from '@/utils/pitchHeatmap'

/** 绘制单色用户曲线 (无参考/通用) */
export function drawUserCurve(
  ctx: CanvasRenderingContext2D,
  points: PitchPoint[],
  color: string,
  timeToX: (t: number) => number,
  freqToY: (f: number) => number,
  windowStart: number,
  windowEnd: number,
): void {
  ctx.strokeStyle = color
  ctx.lineWidth = 3
  ctx.lineJoin = 'round'
  ctx.beginPath()
  let started = false
  for (const point of points) {
    if (point.time < windowStart || point.time > windowEnd) continue
    if (point.frequency <= 0) {
      ctx.stroke()
      started = false
      continue
    }
    const x = timeToX(point.time)
    const y = freqToY(point.frequency)
    if (!started) {
      ctx.beginPath()
      ctx.moveTo(x, y)
      started = true
    } else {
      ctx.globalAlpha = 0.3 + (point.confidence ?? 1) * 0.7
      ctx.lineTo(x, y)
    }
  }
  ctx.globalAlpha = 1
  ctx.stroke()
}

/**
 * 绘制偏差着色曲线 — 逐段按颜色绘制, 静音段灰虚线。
 * 性能模式: 仅每 3 帧取 1 帧着色 (feature: "着色每 3 帧"), 降低绘制开销。
 */
export function drawDeviationCurve(
  ctx: CanvasRenderingContext2D,
  frames: DeviationFrame[],
  timeToX: (t: number) => number,
  freqToY: (f: number) => number,
  windowStart: number,
  windowEnd: number,
  performanceMode = false,
): void {
  /** 最近一个有效音高频率 — 静音段 Y 轴延续 (feature: "不跳变"); 实例内局部变量, 支持多画布复用 */
  let lastValidFreq = 0
  let seg: { color: string; points: Array<{ x: number; y: number }> } | null = null
  let silentPoints: Array<{ x: number; y: number }> = []
  let frameIndex = 0

  function flushSilent(): void {
    if (silentPoints.length === 0) return
    // 静音灰虚线 — 透明度 40% (feature: "#94a3b8, 透明度 40%")
    ctx.save()
    ctx.setLineDash([4, 3])
    ctx.globalAlpha = 0.4
    ctx.strokeStyle = DEVIATION_COLORS.silent
    ctx.lineWidth = 3
    ctx.lineJoin = 'round'
    ctx.beginPath()
    ctx.moveTo(silentPoints[0].x, silentPoints[0].y)
    for (let i = 1; i < silentPoints.length; i++) {
      ctx.lineTo(silentPoints[i].x, silentPoints[i].y)
    }
    ctx.stroke()
    ctx.restore()
    silentPoints = []
  }

  function flush(): void {
    if (!seg) return
    ctx.save()
    ctx.strokeStyle = seg.color
    ctx.lineWidth = 3
    ctx.lineJoin = 'round'
    ctx.beginPath()
    if (seg.points.length > 0) {
      ctx.moveTo(seg.points[0].x, seg.points[0].y)
      for (let i = 1; i < seg.points.length; i++) {
        ctx.lineTo(seg.points[i].x, seg.points[i].y)
      }
    }
    ctx.stroke()
    ctx.restore()
    seg = null
  }

  for (const f of frames) {
    if (f.time < windowStart || f.time > windowEnd) continue
    // 性能模式: 每 3 帧取 1 帧着色 (仅计非静音帧; 静音帧无条件通过, 保证灰虚线连续)
    if (!f.isSilent) frameIndex++
    if (performanceMode && !f.isSilent && frameIndex % 3 !== 0) continue
    if (f.isSilent) {
      flush()
      // 静音帧延续上一个有效音高的 Y 位置 (feature: "不跳变")
      const y = freqToY(lastValidFreq || f.frequency || 220)
      silentPoints.push({ x: timeToX(f.time), y })
      continue
    }
    // 记录有效音高, 供后续静音帧延续
    if (f.frequency > 0) lastValidFreq = f.frequency

    flushSilent()
    if (!seg || seg.color !== f.colorHex) {
      flush()
      seg = { color: f.colorHex, points: [] }
    }
    seg.points.push({ x: timeToX(f.time), y: freqToY(f.frequency) })
  }
  flushSilent()
  flush()
}

/** 偏差热力图条绘制参数 */
export interface HeatmapDrawParams {
  ctx: CanvasRenderingContext2D
  segments: readonly HeatmapSegment[]
  totalDuration: number
  plotLeft: number
  plotTop: number
  plotWidth: number
  barHeight: number
}

/** 底部偏差热力图条 — 全时长横向色条, 颜色密度表示跑调程度 */
export function drawHeatmapBar(p: HeatmapDrawParams): void {
  const { ctx, segments, totalDuration, plotLeft, plotTop, plotWidth, barHeight } = p
  if (segments.length === 0 || totalDuration <= 0 || plotWidth <= 0) return
  ctx.fillStyle = 'rgba(15, 23, 42, 0.9)'
  ctx.fillRect(plotLeft, plotTop, plotWidth, barHeight)
  for (const seg of segments) {
    const x1 = plotLeft + (seg.startTime / totalDuration) * plotWidth
    const x2 = plotLeft + (seg.endTime / totalDuration) * plotWidth
    if (x2 - x1 < 0.5) continue
    ctx.fillStyle = seg.color
    ctx.fillRect(x1, plotTop, x2 - x1, barHeight)
  }
}

/** 低对齐段覆盖绘制参数 */
export interface LowAlignmentDrawParams {
  ctx: CanvasRenderingContext2D
  segments: readonly LowAlignmentSegment[]
  userPoints: readonly PitchPoint[]
  timeToX: (t: number) => number
  freqToY: (f: number) => number
  windowStart: number
  windowEnd: number
  plotTop: number
  plotBottom: number
}

/**
 * DTW 未对齐段覆盖 — 段内用户曲线改为灰色虚线 + 段上方 "⚠️ 对齐不确定"。
 * 绘制在偏差曲线之上 (以灰线掩盖着色), 半透明背景提示段落边界。
 */
export function drawLowAlignmentOverlay(p: LowAlignmentDrawParams): void {
  const {
    ctx,
    segments,
    userPoints,
    timeToX,
    freqToY,
    windowStart,
    windowEnd,
    plotTop,
    plotBottom,
  } = p
  if (segments.length === 0) return
  ctx.save()
  for (const seg of segments) {
    const x1 = timeToX(Math.max(seg.start, windowStart))
    const x2 = timeToX(Math.min(seg.end, windowEnd))
    if (x2 - x1 < 1) continue
    // 半透明背景 — 标记段边界
    ctx.fillStyle = 'rgba(148, 163, 184, 0.08)'
    ctx.fillRect(x1, plotTop, x2 - x1, plotBottom - plotTop)
    // 段内用户曲线 → 灰色虚线 (覆盖在着色曲线上)
    ctx.setLineDash([4, 3])
    ctx.strokeStyle = DEVIATION_COLORS.silent
    ctx.globalAlpha = 0.7
    ctx.lineWidth = 3
    ctx.lineJoin = 'round'
    ctx.beginPath()
    let started = false
    for (const pt of userPoints) {
      if (pt.time < Math.max(seg.start, windowStart) || pt.time > Math.min(seg.end, windowEnd)) continue
      if (pt.frequency <= 0) {
        started = false
        continue
      }
      const x = timeToX(pt.time)
      const y = freqToY(pt.frequency)
      if (!started) {
        ctx.moveTo(x, y)
        started = true
      } else {
        ctx.lineTo(x, y)
      }
    }
    ctx.stroke()
    // "⚠️ 对齐不确定" 标记
    ctx.globalAlpha = 1
    ctx.setLineDash([])
    ctx.fillStyle = '#94a3b8'
    ctx.font = '11px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText('⚠️ 对齐不确定', x1 + 6, plotTop + 14)
  }
  ctx.restore()
}

/** live 模式叠加绘制参数 (Phase 3 录音中实时对比) */
export interface LiveOverlayDrawParams {
  ctx: CanvasRenderingContext2D
  /** 标准参考点 — 非空时绘制偏差色带 */
  refPoints: readonly PitchPoint[]
  /** 用户实时音高点 (与 deviationFrames 下标 1:1) */
  userPoints: readonly PitchPoint[]
  /** 用户偏差帧 — 取颜色/静音判定 */
  deviationFrames: readonly DeviationFrame[]
  /** 当前演唱/播放时间 (秒) — 圆点保留窗口 */
  currentTime: number
  /** 最近偏差 (音分); null 时不显示数值/箭头 */
  liveDeviationCents: number | null
  /** 最近趋势; null 时不显示 */
  liveTrend: PitchTrend | null
  timeToX: (t: number) => number
  freqToY: (f: number) => number
  windowStart: number
  windowEnd: number
  /** 画布 CSS 宽 — 数值文本右对齐锚点 */
  width: number
  /** 绘图区边距 (px) — 右上角文本定位 */
  padding: { top: number; right: number; bottom: number; left: number }
}

/**
 * live 模式绘制 (Phase 3, 录音中) — 偏差色带 + 实时圆点 + 趋势箭头 + 当前音分值。
 * 不绘制完整用户曲线 (feature: "不应显示完整的用户曲线 因为还没唱完")。
 */
export function drawLiveOverlay(p: LiveOverlayDrawParams): void {
  const {
    ctx,
    refPoints,
    userPoints,
    deviationFrames,
    currentTime,
    liveDeviationCents,
    liveTrend,
    timeToX,
    freqToY,
    windowStart,
    windowEnd,
    width,
    padding,
  } = p

  // 1. 偏差背景色带 — 标准线上下 25/50 音分 (绿色/橙色半透明区域)
  if (refPoints.length > 0) {
    drawDeviationBands(ctx, refPoints, timeToX, freqToY, windowStart, windowEnd)
  }

  // 2. 用户实时音高点 — 3px 圆点, 2 秒后淡出; 无声帧不画 (检测不到 ≠ 跑调)
  //    索引遍历 (O(n)): deviationFrames 与 userPoints 1:1 对齐, 直接取帧避免 indexOf 全数组扫描
  const now = currentTime
  const cutoff = now - LIVE_DOT_KEEP_SECONDS
  const frames = deviationFrames
  for (let i = 0; i < userPoints.length; i++) {
    const pt = userPoints[i]
    if (pt.time < cutoff || pt.time > now) continue // 保留窗口 (visibleLivePoints 语义内联)
    if (pt.time < windowStart || pt.time > windowEnd) continue
    if (pt.frequency <= 0) continue
    const frame = frames[i]
    if (frame && frame.isSilent) continue
    const color = frame ? frame.colorHex : DEFAULT_USER_COLOR
    ctx.save()
    ctx.globalAlpha = dotAlpha(now - pt.time)
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(timeToX(pt.time), freqToY(pt.frequency), 3, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  }

  // 3. 当前音分偏差数值 + 趋势箭头 (右上角)
  if (liveDeviationCents !== null && liveTrend !== null) {
    const { symbol, color, label } = trendDisplay(liveTrend)
    ctx.fillStyle = color
    ctx.font = 'bold 22px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText(
      `${symbol} ${formatCentsDeviation(liveDeviationCents)}`,
      width - padding.right,
      padding.top + 26,
    )
    ctx.font = '11px sans-serif'
    ctx.fillText(label, width - padding.right, padding.top + 42)

    // 趋势箭头锚在最近有声点上方 (跟随演唱位置); 锚点在窗口外时跳过 (防绘制到可视区外)
    const latestVoiced = findLatestVoicedPoint(userPoints, frames)
    if (latestVoiced && latestVoiced.time >= windowStart && latestVoiced.time <= windowEnd) {
      ctx.font = 'bold 16px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(symbol, timeToX(latestVoiced.time), freqToY(latestVoiced.frequency) - 10)
    }
  }
}

/** 最近一个有声用户点 — 趋势箭头锚点 (跳过无声帧, 与 latestDeviationCents 一致) */
function findLatestVoicedPoint(
  userPoints: readonly PitchPoint[],
  frames: readonly DeviationFrame[],
): PitchPoint | null {
  for (let i = userPoints.length - 1; i >= 0; i--) {
    const f = frames[i]
    if (f && !f.isSilent) return userPoints[i]
  }
  return null
}

/**
 * 偏差背景色带 (live 模式静态引导) — 围绕标准线嵌套隧道:
 * 最外层 >50 红 (±100 外带) + 25-50 橙 (±50) + ≤25 绿 (±25)。
 * 由内向外叠绘, 后绘者覆盖内带 → 视觉上 0-25 绿 / 25-50 橙 / 50-100 红。
 */
export function drawDeviationBands(
  ctx: CanvasRenderingContext2D,
  refPoints: readonly PitchPoint[],
  timeToX: (t: number) => number,
  freqToY: (f: number) => number,
  windowStart: number,
  windowEnd: number,
): void {
  const pts = refPoints.filter((p) => p.frequency > 0 && p.time >= windowStart && p.time <= windowEnd)
  if (pts.length < 2) return
  drawBand(ctx, pts, 100, 'rgba(239, 68, 68, 0.06)', timeToX, freqToY)
  drawBand(ctx, pts, 50, 'rgba(245, 158, 11, 0.07)', timeToX, freqToY)
  drawBand(ctx, pts, 25, 'rgba(34, 197, 94, 0.10)', timeToX, freqToY)
}

/** 三档偏差填色 (半透明) — feature "偏差区域填色": ≤25 浅绿 / 25-50 浅橙 / >50 浅红 */
const DEVIATION_FILL_COLORS = {
  accurate: 'rgba(34, 197, 94, 0.14)',
  slightBias: 'rgba(245, 158, 11, 0.16)',
  outOfTune: 'rgba(239, 68, 68, 0.18)',
} as const

/** 偏差区域填色绘制参数 (非 live 双轨叠加) */
export interface DeviationFillParams {
  ctx: CanvasRenderingContext2D
  frames: readonly DeviationFrame[]
  timeToX: (t: number) => number
  freqToY: (f: number) => number
  windowStart: number
  windowEnd: number
  /** 性能模式: 跳过填色 (着色曲线已每 3 帧, 进一步降绘制开销) */
  performanceMode?: boolean
}

/**
 * 偏差区域填色 (非 live 双轨, 曲线下方) — 逐帧在标准参考与用户曲线之间填充垂直条,
 * 颜色按绝对音分偏差 (≤25 绿 / 25-50 橙 / >50 红), 半透明保证曲线仍清晰。
 * 连续帧同色 → 视觉上连成带状; 静音/无声帧跳过 (检测不到 ≠ 跑调)。
 */
export function drawDeviationFillBands(p: DeviationFillParams): void {
  const { ctx, frames, timeToX, freqToY, windowStart, windowEnd, performanceMode = false } = p
  if (frames.length === 0 || performanceMode) return
  ctx.save()
  for (let i = 0; i < frames.length; i++) {
    const f = frames[i]
    if (f.time < windowStart || f.time > windowEnd) continue
    if (f.isSilent || f.frequency <= 0 || f.refFrequency <= 0) continue
    const x0 = timeToX(f.time)
    // 槽宽 = 到下一帧的 X 跨度 (末帧取 2px 最小宽度), 使同色相邻帧无缝连成带状
    const x1 = i + 1 < frames.length ? timeToX(frames[i + 1].time) : x0 + 2
    if (x1 <= x0) continue
    const yRef = freqToY(f.refFrequency)
    const yUser = freqToY(f.frequency)
    const height = Math.abs(yUser - yRef)
    if (height < 0.5) continue // 重合帧填色不可见, 跳过
    const absCents = Math.abs(f.centsDeviation)
    ctx.fillStyle =
      absCents <= DEVIATION_THRESHOLDS.accurate
        ? DEVIATION_FILL_COLORS.accurate
        : absCents <= DEVIATION_THRESHOLDS.slightBias
          ? DEVIATION_FILL_COLORS.slightBias
          : DEVIATION_FILL_COLORS.outOfTune
    ctx.fillRect(x0, Math.min(yRef, yUser), Math.max(1, x1 - x0), height)
  }
  ctx.restore()
}

/** 绘制一条音分偏移色带 — 上缘 +cents, 下缘 -cents 围成封闭填充 */
function drawBand(
  ctx: CanvasRenderingContext2D,
  pts: readonly PitchPoint[],
  cents: number,
  color: string,
  timeToX: (t: number) => number,
  freqToY: (f: number) => number,
): void {
  ctx.save()
  ctx.fillStyle = color
  ctx.beginPath()
  pts.forEach((pt, i) => {
    const x = timeToX(pt.time)
    const y = freqToY(freqAtCentsOffset(pt.frequency, cents))
    if (i === 0) ctx.moveTo(x, y)
    else ctx.lineTo(x, y)
  })
  for (let i = pts.length - 1; i >= 0; i--) {
    const x = timeToX(pts[i].time)
    const y = freqToY(freqAtCentsOffset(pts[i].frequency, -cents))
    ctx.lineTo(x, y)
  }
  ctx.closePath()
  ctx.fill()
  ctx.restore()
}

/** 缩略导航条绘制参数 */
export interface ThumbnailDrawParams {
  ctx: CanvasRenderingContext2D
  userPoints: readonly PitchPoint[]
  totalDuration: number
  /** 当前视口 [start, end] 秒 — 高亮框 */
  viewport: { start: number; end: number } | null
  plotLeft: number
  plotTop: number
  plotWidth: number
  thumbHeight: number
  freqToY: (f: number) => number
}

/** 缩略导航条 — 全长用户曲线预览 + 当前视口高亮框 (拖拽 seek 由组件层处理) */
export function drawThumbnail(p: ThumbnailDrawParams): void {
  const { ctx, userPoints, totalDuration, viewport, plotLeft, plotTop, plotWidth, thumbHeight, freqToY } = p
  if (totalDuration <= 0 || plotWidth <= 0) return

  const xFull = (t: number): number => plotLeft + (t / totalDuration) * plotWidth

  // 底槽
  ctx.fillStyle = 'rgba(30, 41, 59, 0.65)'
  ctx.fillRect(plotLeft, plotTop, plotWidth, thumbHeight)

  // 全长用户曲线 (细线聚合)
  ctx.save()
  ctx.strokeStyle = 'rgba(59, 130, 246, 0.55)'
  ctx.lineWidth = 1
  ctx.beginPath()
  let started = false
  for (const pt of userPoints) {
    if (pt.frequency <= 0) {
      started = false
      continue
    }
    const x = xFull(pt.time)
    const y = Math.max(plotTop + 2, Math.min(plotTop + thumbHeight - 2, freqToY(pt.frequency)))
    if (!started) {
      ctx.moveTo(x, y)
      started = true
    } else {
      ctx.lineTo(x, y)
    }
  }
  ctx.stroke()
  ctx.restore()

  // 视口高亮框
  if (viewport && viewport.end > viewport.start) {
    const vx1 = xFull(Math.max(0, viewport.start))
    const vx2 = xFull(Math.min(totalDuration, viewport.end))
    if (vx2 > vx1) {
      ctx.fillStyle = 'rgba(99, 102, 241, 0.18)'
      ctx.fillRect(vx1, plotTop, vx2 - vx1, thumbHeight)
      ctx.strokeStyle = '#6366f1'
      ctx.lineWidth = 1
      ctx.strokeRect(vx1 + 0.5, plotTop + 0.5, vx2 - vx1 - 1, thumbHeight - 1)
    }
  }
}
