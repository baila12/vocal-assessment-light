<script setup lang="ts">
/**
 * PitchComparisonCanvas — 全功能音准对比视口 (v7.13 Phase 2 + Phase 3)
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
 * Props 全部响应式, 组件内部用纯函数 (pitchDeviation/pitchScroll/pitchNotes/pitchLive)
 * 计算, 无业务逻辑 — 便于 Phase 4 回放/Phase 5 CompareView 复用。
 */

import { ref, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import type { PitchPoint } from '@/types/pitch'
import { alignPitchCurves, DEVIATION_COLORS, DEFAULT_USER_COLOR } from '@/utils/pitchDeviation'
import { computeScrollWindow, autoViewportSeconds, autoTickStepSeconds, generateTimeTicks } from '@/utils/pitchScroll'
import { generateNoteTicks, pitchRangeToMidi, type NoteTick } from '@/utils/pitchNotes'
import { clampSeek, wrapInABLoop, type ABLoopRange } from '@/utils/pitchPlayback'
import {
  deviationTrend,
  trendDisplay,
  formatCentsDeviation,
  latestDeviationCents,
  dotAlpha,
  freqAtCentsOffset,
  LIVE_DOT_KEEP_SECONDS,
} from '@/utils/pitchLive'

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
  },
)

const emit = defineEmits<{
  (e: 'ready'): void
  /** 点击画布跳转播放位置 */
  (e: 'seek', time: number): void
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let dpr = 1

/** 绘图区边距 (px) — 左 Y 轴刻度 / 上 / 右 / 下 X 轴刻度 */
const PLOT_PADDING = { top: 20, right: 16, bottom: 24, left: 44 }

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

  const { width, height } = canvas
  ctx.clearRect(0, 0, width, height)

  // 空状态
  if (props.userPitchData.length === 0 && props.refPitchData.length === 0) {
    ctx.fillStyle = '#94a3b8'
    ctx.font = '13px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('暂无音高数据', width / 2, height / 2)
    return
  }

  const padding = PLOT_PADDING
  const plotW = width - padding.left - padding.right
  const plotH = height - padding.top - padding.bottom
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

  // ---- Y 轴: 钢琴键网格 + 白键高亮标注 ----
  ctx.lineWidth = 1
  for (const tick of noteTicks.value) {
    if (tick.midi < 0 || tick.midi > 127) continue
    const f = Math.pow(2, (tick.midi - 69) / 12) * 440
    const y = freqToY(f)
    // 网格线
    ctx.strokeStyle = tick.isWhite ? 'rgba(148, 163, 184, 0.22)' : 'rgba(148, 163, 184, 0.08)'
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(padding.left + plotW, y)
    ctx.stroke()
    // 白键标签 (黑键只画短刻度线, 不标文字避免拥挤)
    if (props.showYAxisLabels && tick.isWhite) {
      ctx.fillStyle = '#94a3b8'
      ctx.font = '10px sans-serif'
      ctx.textAlign = 'right'
      ctx.fillText(tick.name, padding.left - 4, y + 3)
    } else if (props.showYAxisLabels) {
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.35)'
      ctx.beginPath()
      ctx.moveTo(padding.left - 5, y)
      ctx.lineTo(padding.left, y)
      ctx.stroke()
    }
  }

  // ---- X 轴: 时间刻度 ----
  if (props.showTimeAxis) {
    ctx.fillStyle = '#94a3b8'
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'center'
    for (const t of timeTicks.value) {
      const x = timeToX(t)
      if (x < padding.left || x > padding.left + plotW) continue
      ctx.strokeStyle = 'rgba(148, 163, 184, 0.15)'
      ctx.beginPath()
      ctx.moveTo(x, padding.top)
      ctx.lineTo(x, padding.top + plotH)
      ctx.stroke()
      ctx.fillText(`${Math.round(t)}s`, x, height - 6)
    }
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
      drawLiveOverlay(ctx, timeToX, freqToY, windowStart, windowEnd, width)
    }
  } else if (props.userPitchData.length > 0) {
    if (!hasReference.value) {
      // 无参考: 单条蓝色实线, 不显示偏差
      drawUserCurve(ctx, props.userPitchData, DEFAULT_USER_COLOR, timeToX, freqToY, windowStart, windowEnd)
    } else {
      drawDeviationCurve(ctx, deviationFrames.value, timeToX, freqToY, windowStart, windowEnd)
    }
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
}

/** 绘制单色用户曲线 (无参考/通用) */
function drawUserCurve(
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
 * 同一颜色连续帧合并为一段, 颜色在音符边界平滑过渡 (非逐帧跳变)。
 */
function drawDeviationCurve(
  ctx: CanvasRenderingContext2D,
  frames: ReturnType<typeof alignPitchCurves>,
  timeToX: (t: number) => number,
  freqToY: (f: number) => number,
  windowStart: number,
  windowEnd: number,
): void {
  /** 最近一个有效音高频率 — 静音段 Y 轴延续 (feature: "不跳变"); 实例内局部变量, 支持多画布复用 */
  let lastValidFreq = 0
  let seg: { color: string; points: Array<{ x: number; y: number }> } | null = null
  let silentPoints: Array<{ x: number; y: number }> = []

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

/**
 * live 模式绘制 (Phase 3, 录音中) — 偏差色带 + 实时圆点 + 趋势箭头 + 当前音分值。
 * 不绘制完整用户曲线 (feature: "不应显示完整的用户曲线 因为还没唱完")。
 */
function drawLiveOverlay(
  ctx: CanvasRenderingContext2D,
  timeToX: (t: number) => number,
  freqToY: (f: number) => number,
  windowStart: number,
  windowEnd: number,
  width: number,
): void {
  const padding = PLOT_PADDING

  // 1. 偏差背景色带 — 标准线上下 25/50 音分 (绿色/橙色半透明区域)
  if (hasReference.value) {
    drawDeviationBands(ctx, props.refPitchData, timeToX, freqToY, windowStart, windowEnd)
  }

  // 2. 用户实时音高点 — 3px 圆点, 2 秒后淡出; 无声帧不画 (检测不到 ≠ 跑调)
  //    索引遍历 (O(n)): deviationFrames 与 userPitchData 1:1 对齐, 直接取帧避免 indexOf 全数组扫描
  const now = props.currentTime
  const cutoff = now - LIVE_DOT_KEEP_SECONDS
  const frames = deviationFrames.value
  const liveData = props.userPitchData
  for (let i = 0; i < liveData.length; i++) {
    const p = liveData[i]
    if (p.time < cutoff || p.time > now) continue // 保留窗口 (visibleLivePoints 语义内联)
    if (p.time < windowStart || p.time > windowEnd) continue
    if (p.frequency <= 0) continue
    const frame = frames[i]
    if (frame && frame.isSilent) continue
    const color = frame ? frame.colorHex : DEFAULT_USER_COLOR
    ctx.save()
    ctx.globalAlpha = dotAlpha(now - p.time)
    ctx.fillStyle = color
    ctx.beginPath()
    ctx.arc(timeToX(p.time), freqToY(p.frequency), 3, 0, Math.PI * 2)
    ctx.fill()
    ctx.restore()
  }

  // 3. 当前音分偏差数值 + 趋势箭头 (右上角)
  if (liveDeviation.value !== null && liveTrend.value !== null) {
    const { symbol, color, label } = trendDisplay(liveTrend.value)
    ctx.fillStyle = color
    ctx.font = 'bold 22px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText(
      `${symbol} ${formatCentsDeviation(liveDeviation.value)}`,
      width - padding.right,
      padding.top + 26,
    )
    ctx.font = '11px sans-serif'
    ctx.fillText(label, width - padding.right, padding.top + 42)

    // 趋势箭头锚在最近有声点上方 (跟随演唱位置); 锚点在窗口外时跳过 (防绘制到可视区外)
    const latestVoiced = findLatestVoicedPoint()
    if (latestVoiced && latestVoiced.time >= windowStart && latestVoiced.time <= windowEnd) {
      ctx.font = 'bold 16px sans-serif'
      ctx.textAlign = 'center'
      ctx.fillText(symbol, timeToX(latestVoiced.time), freqToY(latestVoiced.frequency) - 10)
    }
  }
}

/** 最近一个有声用户点 — 趋势箭头锚点 (跳过无声帧, 与 latestDeviationCents 一致) */
function findLatestVoicedPoint(): PitchPoint | null {
  const frames = deviationFrames.value
  for (let i = props.userPitchData.length - 1; i >= 0; i--) {
    const f = frames[i]
    if (f && !f.isSilent) return props.userPitchData[i]
  }
  return null
}

/** 偏差背景色带 — 围绕标准线 ±50 橙色外带 + ±25 绿色内带 (半透明填充) */
function drawDeviationBands(
  ctx: CanvasRenderingContext2D,
  refPoints: PitchPoint[],
  timeToX: (t: number) => number,
  freqToY: (f: number) => number,
  windowStart: number,
  windowEnd: number,
): void {
  const pts = refPoints.filter((p) => p.frequency > 0 && p.time >= windowStart && p.time <= windowEnd)
  if (pts.length < 2) return
  drawBand(ctx, pts, 50, 'rgba(245, 158, 11, 0.07)', timeToX, freqToY)
  drawBand(ctx, pts, 25, 'rgba(34, 197, 94, 0.10)', timeToX, freqToY)
}

/** 绘制一条音分偏移色带 — 上缘 +cents, 下缘 -cents 围成封闭填充 */
function drawBand(
  ctx: CanvasRenderingContext2D,
  pts: PitchPoint[],
  cents: number,
  color: string,
  timeToX: (t: number) => number,
  freqToY: (f: number) => number,
): void {
  ctx.save()
  ctx.fillStyle = color
  ctx.beginPath()
  pts.forEach((p, i) => {
    const x = timeToX(p.time)
    const y = freqToY(freqAtCentsOffset(p.frequency, cents))
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

/** 画布点击 → 计算时间位置并 emit seek (Phase 2: 拖拽/点击跳转) */
function onClickCanvas(e: MouseEvent): void {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const padding = PLOT_PADDING
  const plotW = rect.width - padding.left - padding.right
  if (plotW <= 0) return
  const { windowStart, windowEnd } = windowInfo.value
  const ratio = Math.max(0, Math.min(1, (e.offsetX - padding.left) / plotW))
  const target = windowStart + ratio * (windowEnd - windowStart)
  emit('seek', Math.round(target * 100) / 100)
}

/** 键盘跳转 — 方向键 ±1s / Shift+方向键 ±5s (a11y, 与点击 seek 等效) */
function onCanvasKeydown(e: KeyboardEvent): void {
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

// 重绘触发: 数据 / 播放位置 / 视口 / 循环区间 / live 模式
const drawTrigger = computed(() => ({
  user: props.userPitchData,
  ref: props.refPitchData,
  time: props.currentTime,
  loop: props.abLoop,
  viewport: viewportSeconds.value,
  live: props.liveMode,
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
    aria-label="音准对比曲线图，点击或使用方向键跳转播放位置"
    tabindex="0"
    @click="onClickCanvas"
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
