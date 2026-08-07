<script setup lang="ts">
/**
 * PitchComparisonCanvas — 全功能音准对比视口 (v7.13 Phase 2 + Phase 3 + Phase 4)
 *
 * 对齐 pitch-realtime.feature:
 *   回放模式 (默认, Phase 2, 第一~三章):
 *   - 双曲线: 参考虚线 #6366f1 2px / 用户偏差着色 3px
 *   - 偏差着色: ≤25 绿 / 25-50 橙 / >50 红 (逐段绘制, 静音灰虚线)
 *   - 滚动窗口: 播放位置居中, 从右向左滚动 (computeScrollWindow)
 *   - Y 轴: C3-B5 钢琴键白键高亮 (对数频率刻度)
 *   - X 轴: 时间秒刻度
 *   - 无参考: 单条蓝色 #3b82f6 曲线 + "绝对音高 (无参考)"
 *   - 八度跳变: ⚠️ 标记 (可能误检)
 *   - 播放游标: 当前播放位置竖线
 *
 *   live 模式 (liveMode prop, Phase 3, 录音中实时对比):
 *   - 标准音高虚线滚动 (与伴奏同步)
 *   - 用户实时音高点: 3px 圆点, 2 秒后淡出 (保留窗口 + dotAlpha 线性淡出)
 *   - 偏差背景色带: 标准线上下 25/50 音分 绿色/橙色半透明区域
 *   - 当前音分偏差数值: 右上角 "+15 音分"
 *   - 音高趋势箭头: 偏高 ↑ 红 / 偏低 ↓ 蓝 / 精准 ✓ 绿 (deviationTrend/trendDisplay)
 *   - 不绘制完整用户曲线 (还没唱完)
 *
 *   Phase 4 (回放分析, 非 live + 有参考):
 *   - 问题段落红色半透明背景高亮 (偏差 >50 音分持续 >0.5s, findProblemSegments)
 *   - 逐句音准评分标签浮在乐句上方 (segmentPhrases + scorePhrase + phraseScoreColor)
 *
 * Props 全部响应式, 组件内部用纯函数 (pitchDeviation/pitchScroll/pitchNotes/pitchLive/pitchSegments)
 * 计算, 无业务逻辑 — 便于 Phase 5 CompareView 复用。
 */

import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import type { PitchPoint, LowAlignmentSegment } from '@/types/pitch'
import { alignPitchCurves, DEFAULT_USER_COLOR } from '@/utils/pitchDeviation'
import { computeScrollWindow, autoViewportSeconds, autoTickStepSeconds, generateTimeTicks } from '@/utils/pitchScroll'
import { generateNoteTicks, pitchRangeToMidi, type NoteTick } from '@/utils/pitchNotes'
import { clampSeek, wrapInABLoop, type ABLoopRange } from '@/utils/pitchPlayback'
import { heatmapClickToTime, type HeatmapSegment } from '@/utils/pitchHeatmap'
import {
  drawUserCurve,
  drawDeviationCurve,
  drawDeviationFillBands,
  drawHeatmapBar,
  drawLowAlignmentOverlay,
  drawLiveOverlay,
  drawThumbnail,
} from '@/utils/pitchCompareDraw'
import { deviationTrend, latestDeviationCents } from '@/utils/pitchLive'
import {
  findProblemSegments,
  segmentPhrases,
  scorePhrase,
  phraseScoreColor,
  type TimeRange,
} from '@/utils/pitchSegments'

const props = withDefaults(
  defineProps<{
    userPitchData: PitchPoint[]
    refPitchData?: PitchPoint[]
    currentTime?: number
    totalDuration?: number
    height?: number
    refLineColor?: string
    cursorColor?: string
    showReference?: boolean
    showYAxisLabels?: boolean
    showTimeAxis?: boolean
    /** 录音中实时对比模式 (Phase 3) — 圆点/色带/趋势箭头, 不画完整曲线 */
    liveMode?: boolean
    /** A-B 循环区间 (Phase 2 播放控制) */
    abLoop?: ABLoopRange | null
    /** 无参考时的标题提示 (feature: "绝对音高 (无参考)") */
    noRefTitle?: string
    /** 性能模式 (Phase 5) — 抗锯齿关 / 着色每 3 帧 / 网格关 / 缩略条关 */
    performanceMode?: boolean
    /** 底部偏差热力图桶 (Phase 5) — 颜色密度表示跑调程度, 点击跳转 */
    heatmapSegments?: readonly HeatmapSegment[]
    /** DTW 低对齐段 (Phase 5) — 段内灰色虚线 + ⚠️ 对齐不确定 */
    lowAlignmentSegments?: readonly LowAlignmentSegment[]
    /** 缩略导航条 (Phase 5 长音频) — 全长预览 + 视口高亮 + 拖拽 seek */
    showThumbnail?: boolean
  }>(),
  {
    refPitchData: () => [],
    currentTime: 0,
    totalDuration: 0,
    height: 240,
    refLineColor: '#6366f1',
    cursorColor: '#ef4444',
    showReference: true,
    showYAxisLabels: true,
    showTimeAxis: true,
    liveMode: false,
    abLoop: null,
    noRefTitle: '绝对音高 (无参考)',
    performanceMode: false,
    heatmapSegments: () => [],
    lowAlignmentSegments: () => [],
    showThumbnail: false,
  },
)

const emit = defineEmits<{
  (e: 'ready'): void
  /** 点击画布跳转播放位置 */
  (e: 'seek', time: number): void
  /** 缩略导航条拖拽/点击 seek (Phase 5) */
  (e: 'thumbnailSeek', time: number): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let dpr = 1

/** 绘图区边距 (px) — 左 Y 轴刻度 / 上 / 右 / 下 X 轴刻度 */
const PLOT_PADDING = { top: 20, right: 16, bottom: 24, left: 44 }

/** 偏差热力图条高度 (px) */
const HEATMAP_BAR_HEIGHT = 20
/** 缩略导航条高度 (px) */
const THUMBNAIL_BAR_HEIGHT = 44
/** 底部条与绘图区间距 (px) */
const BAR_GAP = 6

/** 底部条几何 — 依 props 动态计算绘图区 padding 与热力图/缩略条的 y 位置 (CSS px) */
function bottomBarsGeometry(widthCss: number, heightCss: number): {
  padding: { top: number; right: number; bottom: number; left: number }
  plotW: number
  plotH: number
  heatmapY: number
  thumbY: number
  hasHeatmap: boolean
  hasThumb: boolean
} {
  const hasHeatmap = props.heatmapSegments.length > 0
  const hasThumb = props.showThumbnail && !props.performanceMode
  const padding = {
    ...PLOT_PADDING,
    bottom:
      PLOT_PADDING.bottom +
      (hasHeatmap ? HEATMAP_BAR_HEIGHT + BAR_GAP : 0) +
      (hasThumb ? THUMBNAIL_BAR_HEIGHT + BAR_GAP : 0),
  }
  const plotW = Math.max(0, widthCss - padding.left - padding.right)
  const plotH = Math.max(0, heightCss - padding.top - padding.bottom)
  const baseBottomY = padding.top + plotH
  const heatmapY = hasHeatmap ? baseBottomY + PLOT_PADDING.bottom + BAR_GAP : 0
  const thumbY = hasThumb ? heatmapY + HEATMAP_BAR_HEIGHT + BAR_GAP : 0
  return { padding, plotW, plotH, heatmapY, thumbY, hasHeatmap, hasThumb }
}

/** 无参考判定 — 参考曲线为空 */
const hasReference = computed(() => props.refPitchData.length > 0)

/** 总时长 — 显式传入优先, 否则取两曲线最大时间 */
const effectiveDuration = computed(() => {
  if (props.totalDuration > 0) return props.totalDuration
  const times = [...props.userPitchData, ...props.refPitchData].map((d) => d.time)
  return times.length ? Math.max(...times) : 0
})

/** 视口宽度 — 自动: 短音频全曲, 长音频 15s */
const viewportSeconds = computed(() =>
  Math.max(1, autoViewportSeconds(effectiveDuration.value)),
)

/** 滚动窗口 — 播放位置居中 */
const windowInfo = computed(() =>
  computeScrollWindow({
    viewportSeconds: viewportSeconds.value,
    totalDuration: effectiveDuration.value,
    currentTime: clampSeek(wrapInABLoop(props.currentTime, props.abLoop), effectiveDuration.value),
  }),
)

/** 用户偏差帧 — 有参考时逐帧着色 */
const deviationFrames = computed(() => {
  if (!hasReference.value) return []
  return alignPitchCurves(props.userPitchData, props.refPitchData)
})

/** 问题段落 (回放模式 + 有参考) — 偏差 >50 音分持续 >0.5s (feature: 红色半透明背景高亮) */
const problemSegments = computed<TimeRange[]>(() => {
  if (props.liveMode || !hasReference.value) return []
  return findProblemSegments(deviationFrames.value)
})

/** 逐句音准评分 (回放模式 + 有参考) — 参考曲线静音间隙切分乐句, 每句一个分数标签 */
const phraseScores = computed<Array<{ start: number; end: number; score: number; maxFreq: number }>>(() => {
  if (props.liveMode || !hasReference.value) return []
  const frames = deviationFrames.value
  const scores: Array<{ start: number; end: number; score: number; maxFreq: number }> = []
  for (const phrase of segmentPhrases(props.refPitchData)) {
    const score = scorePhrase(frames, phrase.start, phrase.end)
    if (score === null) continue
    // 预计算乐句内参考最高音 (静态数据) — 避免 draw() 每帧 O(乐句×参考点) 扫描 (审查 MEDIUM)
    let maxFreq = 0
    for (const p of props.refPitchData) {
      if (p.frequency <= 0 || p.time < phrase.start || p.time > phrase.end) continue
      if (p.frequency > maxFreq) maxFreq = p.frequency
    }
    scores.push({ start: phrase.start, end: phrase.end, score, maxFreq })
  }
  return scores
})

/** live 模式最近偏差 (音分) — 最新有声帧; 无参考/全静音 → null */
const liveDeviation = computed<number | null>(() => {
  if (!hasReference.value) return null
  return latestDeviationCents(deviationFrames.value)
})

/** live 模式最近趋势 — 偏差 → 偏高/偏低/精准 */
const liveTrend = computed(() => {
  const dev = liveDeviation.value
  return dev === null ? null : deviationTrend(dev)
})

/** Y 轴音高刻度 — 合并两曲线频率范围 → C3-B5 半音 */
const noteTicks = computed<NoteTick[]>(() => {
  const range = pitchRangeToMidi([...props.userPitchData, ...props.refPitchData])
  if (!range) return []
  // 上下各扩展 2 个半音留白
  return generateNoteTicks(range.minMidi - 2, range.maxMidi + 2)
})

/** X 轴时间刻度 */
const timeTicks = computed(() => {
  const step = autoTickStepSeconds(viewportSeconds.value)
  return generateTimeTicks(effectiveDuration.value, step)
})

function draw(): void {
  const canvas = canvasRef.value
  if (!canvas) return
  // DPR 自愈: 跨显示器拖动/浏览器缩放改变 devicePixelRatio → 重新初始化缓冲 (防模糊/超采样)
  if ((window.devicePixelRatio || 1) !== dpr) {
    initCanvas()
    return
  }
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  // CSS 像素尺寸 — canvas.width/height 为物理像素 (initCanvas ×dpr + ctx.scale),
  // 几何计算除以 dpr 才能落在缩放后的坐标空间 (审查 CRITICAL: HiDPI 全图错位)
  const width = canvas.width / dpr
  const height = canvas.height / dpr
  ctx.clearRect(0, 0, width, height)
  // 性能模式: 关闭抗锯齿 (feature: "抗锯齿关闭") — 降低低端设备渲染开销
  ctx.imageSmoothingEnabled = !props.performanceMode

  // 空状态
  if (props.userPitchData.length === 0 && props.refPitchData.length === 0) {
    ctx.fillStyle = '#94a3b8'
    ctx.font = '13px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('暂无音高数据', width / 2, height / 2)
    return
  }

  const { padding, plotW, plotH, heatmapY, thumbY, hasHeatmap, hasThumb } = bottomBarsGeometry(width, height)
  const { windowStart, windowEnd, cursorXFraction } = windowInfo.value
  const winRange = Math.max(windowEnd - windowStart, 1e-6)

  // ---- 频率范围 (对数刻度, 由音高刻度决定) ----
  const midiRange = pitchRangeToMidi([...props.userPitchData, ...props.refPitchData])
  const freqMin = midiRange ? Math.pow(2, (midiRange.minMidi - 3 - 69) / 12) * 440 : 50
  const freqMax = midiRange ? Math.pow(2, (midiRange.maxMidi + 3 - 69) / 12) * 440 : 1200

  const freqToY = (f: number): number => {
    const logMin = Math.log2(freqMin)
    const logMax = Math.log2(freqMax)
    const logF = Math.log2(Math.max(f, freqMin))
    return padding.top + plotH * (1 - (logF - logMin) / (logMax - logMin))
  }
  const timeToX = (t: number): number =>
    padding.left + ((t - windowStart) / winRange) * plotW

  // ---- 背景 ----
  ctx.fillStyle = '#0f172a'
  ctx.fillRect(padding.left, padding.top, plotW, plotH)

  // ---- Y 轴: 钢琴键网格 + 白键高亮标注 (性能模式跳过网格线, 保留标注) ----
  ctx.lineWidth = 1
  for (const tick of noteTicks.value) {
    if (tick.midi < 0 || tick.midi > 127) continue
    const f = Math.pow(2, (tick.midi - 69) / 12) * 440
    const y = freqToY(f)
    // 网格线 (性能模式关闭 — feature: "网格关闭")
    if (!props.performanceMode) {
      ctx.strokeStyle = tick.isWhite ? 'rgba(148, 163, 184, 0.22)' : 'rgba(148, 163, 184, 0.08)'
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(padding.left + plotW, y)
      ctx.stroke()
    }
    // 白键标签 (黑键只画短刻度线, 不标文字避免拥挤)
    if (props.showYAxisLabels && tick.isWhite) {
      ctx.fillStyle = '#94a3b8'
      ctx.font = '10px sans-serif'
      ctx.textAlign = 'right'
      ctx.fillText(tick.name, padding.left - 4, y + 3)
    } else if (props.showYAxisLabels && !props.performanceMode) {
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.35)'
      ctx.beginPath()
      ctx.moveTo(padding.left - 5, y)
      ctx.lineTo(padding.left, y)
      ctx.stroke()
    }
  }

  // ---- X 轴: 时间刻度 (性能模式跳过纵向网格线, 保留刻度) ----
  if (props.showTimeAxis) {
    ctx.fillStyle = '#94a3b8'
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'center'
    for (const t of timeTicks.value) {
      const x = timeToX(t)
      if (x < padding.left || x > padding.left + plotW) continue
      if (!props.performanceMode) {
        ctx.strokeStyle = 'rgba(148, 163, 184, 0.15)'
        ctx.beginPath()
        ctx.moveTo(x, padding.top)
        ctx.lineTo(x, padding.top + plotH)
        ctx.stroke()
      }
      ctx.fillText(`${Math.round(t)}s`, x, height - 6)
    }
  }

  // ---- 问题段落红色半透明背景高亮 (Phase 4) — 曲线下方, 仅窗口相交部分 ----
  drawProblemSegments(ctx, timeToX, windowStart, windowEnd, padding.top, padding.top + plotH)

  // ---- 偏差区域填色 (Phase 5 双轨叠加) — 标准↔用户 之间按偏差幅值三色填充, 曲线下方 ----
  if (!props.liveMode && props.showReference && hasReference.value && deviationFrames.value.length > 0) {
    drawDeviationFillBands({
      ctx,
      frames: deviationFrames.value,
      timeToX,
      freqToY,
      windowStart,
      windowEnd,
      performanceMode: props.performanceMode,
    })
  }

  // ---- 标准参考曲线 — 虚线 #6366f1 (2px) ----
  if (props.showReference && hasReference.value) {
    ctx.save()
    ctx.setLineDash([6, 4])
    ctx.strokeStyle = props.refLineColor
    ctx.lineWidth = 2
    ctx.lineJoin = 'round'
    ctx.beginPath()
    let started = false
    for (const point of props.refPitchData) {
      if (point.time < windowStart || point.time > windowEnd) continue
      const x = timeToX(point.time)
      const y = freqToY(point.frequency)
      if (point.frequency <= 0) {
        ctx.stroke()
        started = false
        continue
      }
      if (!started) {
        ctx.beginPath()
        ctx.moveTo(x, y)
        started = true
      } else {
        ctx.lineTo(x, y)
      }
    }
    ctx.stroke()
    ctx.restore()
  }

  // ---- 用户音高: live 模式实时圆点 (Phase 3) / 回放模式完整曲线 ----
  if (props.liveMode) {
    if (props.userPitchData.length > 0) {
      drawLiveOverlay({
        ctx,
        refPoints: props.refPitchData,
        userPoints: props.userPitchData,
        deviationFrames: deviationFrames.value,
        currentTime: props.currentTime,
        liveDeviationCents: liveDeviation.value,
        liveTrend: liveTrend.value,
        timeToX,
        freqToY,
        windowStart,
        windowEnd,
        width,
        padding,
      })
    }
  } else if (props.userPitchData.length > 0) {
    if (!hasReference.value) {
      // 无参考: 单条蓝色实线, 不显示偏差
      drawUserCurve(ctx, props.userPitchData, DEFAULT_USER_COLOR, timeToX, freqToY, windowStart, windowEnd)
    } else {
      // 性能模式: 着色每 3 帧 (feature: 降低绘制开销)
      drawDeviationCurve(ctx, deviationFrames.value, timeToX, freqToY, windowStart, windowEnd, props.performanceMode)
    }
  }

  // ---- DTW 未对齐段覆盖 (Phase 5) — 段内灰虚线 + ⚠️ 对齐不确定 ----
  if (!props.liveMode && props.lowAlignmentSegments.length > 0) {
    drawLowAlignmentOverlay({
      ctx,
      segments: props.lowAlignmentSegments,
      userPoints: props.userPitchData,
      timeToX,
      freqToY,
      windowStart,
      windowEnd,
      plotTop: padding.top,
      plotBottom: padding.top + plotH,
    })
  }

  // ---- 八度跳变 ⚠️ 标记 ----
  if (hasReference.value) {
    for (const f of deviationFrames.value) {
      if (!f.isOctaveJump) continue
      if (f.time < windowStart || f.time > windowEnd) continue
      const x = timeToX(f.time)
      const y = freqToY(f.frequency) - 8
      ctx.fillStyle = '#f59e0b'
      ctx.font = '11px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText('⚠️', x, Math.max(padding.top + 8, y))
    }
  }

  // ---- 逐句音准评分标签 (Phase 4) — 浮在乐句上方 ----
  drawPhraseScores(ctx, timeToX, freqToY, windowStart, windowEnd, padding.left, plotW, padding.top, plotH)

  // ---- 播放游标 (当前播放位置, 居中标尺) ----
  const cx = padding.left + cursorXFraction * plotW
  ctx.beginPath()
  ctx.strokeStyle = props.cursorColor
  ctx.lineWidth = 2
  ctx.moveTo(cx, padding.top)
  ctx.lineTo(cx, padding.top + plotH)
  ctx.stroke()

  // ---- 无参考标题 (feature: "绝对音高 (无参考)") ----
  if (!hasReference.value && props.showYAxisLabels) {
    ctx.fillStyle = 'rgba(59, 130, 246, 0.9)'
    ctx.font = '11px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText(props.noRefTitle, padding.left + 6, padding.top + 12)
  }

  // ---- 底部偏差热力图条 (Phase 5) — 全时长, 颜色密度表示跑调程度 ----
  if (hasHeatmap) {
    drawHeatmapBar({
      ctx,
      segments: props.heatmapSegments,
      totalDuration: effectiveDuration.value,
      plotLeft: padding.left,
      plotTop: heatmapY,
      plotWidth: plotW,
      barHeight: HEATMAP_BAR_HEIGHT,
    })
  }

  // ---- 缩略导航条 (Phase 5 长音频) — 全长预览 + 视口高亮 (性能模式关闭 — feature: "缩略条关闭") ----
  if (hasThumb) {
    drawThumbnail({
      ctx,
      userPoints: props.userPitchData,
      totalDuration: effectiveDuration.value,
      viewport: { start: windowStart, end: windowEnd },
      plotLeft: padding.left,
      plotTop: thumbY,
      plotWidth: plotW,
      thumbHeight: THUMBNAIL_BAR_HEIGHT,
      freqToY,
    })
  }
}

/**
 * 问题段落红色半透明背景高亮 (Phase 4) — 仅绘制与当前窗口相交的部分。
 * 覆盖在曲线下方 (背景), 点击仍由 onClickCanvas 全画布 seek 处理。
 */
function drawProblemSegments(
  ctx: CanvasRenderingContext2D,
  timeToX: (t: number) => number,
  windowStart: number,
  windowEnd: number,
  plotTop: number,
  plotBottom: number,
): void {
  if (problemSegments.value.length === 0) return
  ctx.save()
  ctx.fillStyle = 'rgba(239, 68, 68, 0.10)'
  for (const seg of problemSegments.value) {
    const x1 = timeToX(Math.max(seg.start, windowStart))
    const x2 = timeToX(Math.min(seg.end, windowEnd))
    if (x2 <= x1) continue
    ctx.fillRect(x1, plotTop, x2 - x1, plotBottom - plotTop)
  }
  ctx.restore()
}

/**
 * 逐句音准评分标签 (Phase 4) — 每句一个分数药丸, 浮在乐句参考曲线最高音上方。
 * 深底浅文保证暗背景可读性 (a11y), 药丸居中于乐句, 越界裁剪在绘图区内。
 */
function drawPhraseScores(
  ctx: CanvasRenderingContext2D,
  timeToX: (t: number) => number,
  freqToY: (f: number) => number,
  windowStart: number,
  windowEnd: number,
  plotLeft: number,
  plotWidth: number,
  plotTop: number,
  plotHeight: number,
): void {
  if (phraseScores.value.length === 0) return
  ctx.save()
  ctx.font = 'bold 12px sans-serif'
  ctx.textAlign = 'center'
  for (const ps of phraseScores.value) {
    if (ps.end < windowStart || ps.start > windowEnd) continue
    const cx = (timeToX(Math.max(ps.start, windowStart)) + timeToX(Math.min(ps.end, windowEnd))) / 2
    const label = `${ps.score}`
    const tw = ctx.measureText(label).width
    const bw = tw + 12
    const bh = 17
    const bx = Math.min(Math.max(cx - bw / 2, plotLeft + 2), plotLeft + plotWidth - bw - 2)
    // 最高音在视口外时 Y 可能越界 — 钳制在绘图区顶/底部 (a11y: 标签始终可读)
    const rawBy = (ps.maxFreq > 0 ? freqToY(ps.maxFreq) : plotTop + 14) - bh - 4
    const by = Math.min(Math.max(rawBy, plotTop + 2), plotTop + plotHeight - bh - 2)
    // 药丸背景 (深底) + 分数颜色边框与文字 — 暗背景可读
    ctx.fillStyle = 'rgba(15, 23, 42, 0.88)'
    ctx.strokeStyle = phraseScoreColor(ps.score)
    ctx.lineWidth = 1
    ctx.beginPath()
    // roundRect 兼容性回退 (Safari<16/FF<112) — 防止整个渲染管线中断 (审查 MEDIUM)
    if (typeof ctx.roundRect === 'function') ctx.roundRect(bx, by, bw, bh, 5)
    else ctx.rect(bx, by, bw, bh)
    ctx.fill()
    ctx.stroke()
    ctx.fillStyle = phraseScoreColor(ps.score)
    ctx.fillText(label, bx + bw / 2, by + bh - 5)
  }
  ctx.restore()
}


function initCanvas(): void {
  const canvas = canvasRef.value
  if (!canvas) return
  dpr = window.devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  canvas.width = Math.max(1, Math.round(rect.width * dpr))
  canvas.height = Math.round(props.height * dpr)
  const ctx = canvas.getContext('2d')
  if (ctx) ctx.scale(dpr, dpr)
  draw()
  emit('ready')
}

/** 缩略条拖拽状态 — pointerdown 进入, pointerup/leave 退出 */
let thumbDragging = false

/** 底部条 (热力图/缩略条) 命中检测 — 返回 'heatmap' | 'thumbnail' | null */
function hitBottomBar(e: MouseEvent, rect: DOMRect): 'heatmap' | 'thumbnail' | null {
  const { heatmapY, thumbY, hasHeatmap, hasThumb } = bottomBarsGeometry(rect.width, rect.height)
  const y = e.offsetY
  if (hasHeatmap && y >= heatmapY && y <= heatmapY + HEATMAP_BAR_HEIGHT) return 'heatmap'
  if (hasThumb && y >= thumbY && y <= thumbY + THUMBNAIL_BAR_HEIGHT) return 'thumbnail'
  return null
}

/** 画布点击 → 计算时间位置并 emit seek (Phase 2: 拖拽/点击跳转) */
function onClickCanvas(e: MouseEvent): void {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const { padding, plotW, windowStart, windowEnd } = geometryForClick(rect)
  if (plotW <= 0) return

  // 底部条点击: 热力图全时长 seek / 缩略条 seek (Phase 5)
  const barHit = hitBottomBar(e, rect)
  if (barHit === 'heatmap') {
    const ratio = Math.max(0, Math.min(1, (e.offsetX - padding.left) / plotW))
    emit('seek', Math.round(heatmapClickToTime(ratio, effectiveDuration.value) * 100) / 100)
    return
  }
  if (barHit === 'thumbnail') {
    seekFromThumbEvent(e, rect)
    return
  }

  const ratio = Math.max(0, Math.min(1, (e.offsetX - padding.left) / plotW))
  const target = windowStart + ratio * (windowEnd - windowStart)
  emit('seek', Math.round(target * 100) / 100)
}

/** 点击/拖拽几何 — 与 draw() 共享动态 padding 计算 */
function geometryForClick(rect: DOMRect): {
  padding: { top: number; right: number; bottom: number; left: number }
  plotW: number
  windowStart: number
  windowEnd: number
} {
  const { padding, plotW } = bottomBarsGeometry(rect.width, rect.height)
  const { windowStart, windowEnd } = windowInfo.value
  return { padding, plotW, windowStart, windowEnd }
}

/** 缩略条拖拽 seek — 全时长比例 → emit thumbnailSeek */
function seekFromThumbEvent(e: MouseEvent, rect: DOMRect): void {
  const { padding, plotW } = bottomBarsGeometry(rect.width, rect.height)
  if (plotW <= 0) return
  const ratio = Math.max(0, Math.min(1, (e.offsetX - padding.left) / plotW))
  emit('thumbnailSeek', Math.round(ratio * effectiveDuration.value * 100) / 100)
}

/** 缩略条按下 — 开始拖拽并立即 seek */
function onPointerDown(e: PointerEvent): void {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  if (hitBottomBar(e as MouseEvent, rect) === 'thumbnail') {
    thumbDragging = true
    seekFromThumbEvent(e as MouseEvent, rect)
    canvas.setPointerCapture(e.pointerId)
  }
}

/** 缩略条拖动 — 拖拽中持续 seek */
function onPointerMove(e: PointerEvent): void {
  if (!thumbDragging) return
  const canvas = canvasRef.value
  if (!canvas) return
  seekFromThumbEvent(e as MouseEvent, canvas.getBoundingClientRect())
}

/** 结束拖拽 */
function onPointerUp(e: PointerEvent): void {
  thumbDragging = false
  const canvas = canvasRef.value
  if (canvas && canvas.hasPointerCapture(e.pointerId)) canvas.releasePointerCapture(e.pointerId)
}

/** 键盘跳转 — 方向键 ±1s / Shift+方向键 ±5s (a11y, 与点击 seek 等效) */
function onCanvasKeydown(e: KeyboardEvent): void {
  // 修饰键组合 (Ctrl/Meta/Alt) 不拦截 — 交还浏览器 (如 Alt+← 后退), 与窗口层 mapKeyboardAction 一致
  if (e.ctrlKey || e.metaKey || e.altKey) return
  let delta: number | null = null
  if (e.key === 'ArrowLeft') delta = e.shiftKey ? -5 : -1
  else if (e.key === 'ArrowRight') delta = e.shiftKey ? 5 : 1
  if (delta === null) return
  e.preventDefault()
  emit('seek', clampSeek(props.currentTime + delta, effectiveDuration.value))
}

let resizeObserver: ResizeObserver | null = null

onMounted(() => {
  initCanvas()
  // 容器尺寸变化 → 重新初始化画布 (修复窗口缩放后失真/点击 seek 错位)
  resizeObserver = new ResizeObserver((entries) => {
    for (const entry of entries) {
      const canvas = canvasRef.value
      if (!canvas) continue
      const currentDpr = window.devicePixelRatio || 1
      if (currentDpr !== dpr || Math.abs(entry.contentRect.width * currentDpr - canvas.width) > 1) {
        initCanvas()
        return
      }
    }
  })
  if (canvasRef.value) resizeObserver.observe(canvasRef.value)
})

onBeforeUnmount(() => {
  resizeObserver?.disconnect()
  resizeObserver = null
})

// 重绘触发: 数据 / 播放位置 / 视口 / 循环区间 / live 模式 / 性能模式 / 底部条
const drawTrigger = computed(() => ({
  user: props.userPitchData,
  ref: props.refPitchData,
  time: props.currentTime,
  loop: props.abLoop,
  viewport: viewportSeconds.value,
  live: props.liveMode,
  perf: props.performanceMode,
  heatmap: props.heatmapSegments,
  lowAlign: props.lowAlignmentSegments,
  thumb: props.showThumbnail,
}))

watch(drawTrigger, () => {
  if (canvasRef.value && canvasRef.value.height !== props.height * dpr) {
    initCanvas()
  } else {
    draw()
  }
})
</script>

<template>
  <canvas
    ref="canvasRef"
    class="pitch-comparison-canvas"
    :style="{ height: height + 'px' }"
    role="img"
    aria-label="音准对比曲线图，点击或使用方向键跳转播放位置；底部热力图和缩略条支持点击拖拽"
    tabindex="0"
    @click="onClickCanvas"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
    @keydown="onCanvasKeydown"
  />
</template>

<style scoped>
.pitch-comparison-canvas {
  width: 100%;
  border-radius: var(--el-border-radius-base);
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
}
.pitch-comparison-canvas:focus-visible {
  outline: 2px solid var(--el-color-primary);
  outline-offset: 2px;
}
</style>
