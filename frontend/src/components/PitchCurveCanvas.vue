<script setup lang="ts">
/**
 * PitchCurveCanvas — 音高曲线 Canvas 组件
 *
 * 渲染 PYIN 提取的音高轨迹，支持播放游标
 * Props: pitchData (frequencies + times), currentTime (可选，播放联动)
 */

import { ref, watch, onMounted } from 'vue'
import type { PropType } from 'vue'

export interface PitchPoint {
  time: number
  frequency: number
  confidence?: number
}

const props = defineProps({
  pitchData: {
    type: Array as PropType<PitchPoint[]>,
    required: true,
  },
  currentTime: {
    type: Number,
    default: 0,
  },
  height: {
    type: Number,
    default: 200,
  },
  lineColor: {
    type: String,
    default: '#6366f1',
  },
  cursorColor: {
    type: String,
    default: '#ef4444',
  },
})

const canvasRef = ref<HTMLCanvasElement | null>(null)
let dpr = 1

function draw(): void {
  const canvas = canvasRef.value
  if (!canvas) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const { width, height } = canvas
  const data = props.pitchData

  if (data.length === 0) {
    ctx.clearRect(0, 0, width, height)
    // 绘制空状态
    ctx.fillStyle = '#94a3b8'
    ctx.font = '13px sans-serif'
    ctx.textAlign = 'center'
    ctx.fillText('暂无音高数据', width / 2, height / 2)
    return
  }

  ctx.clearRect(0, 0, width, height)

  const padding = { top: 20, right: 16, bottom: 24, left: 40 }
  const plotW = width - padding.left - padding.right
  const plotH = height - padding.top - padding.bottom

  // 坐标范围
  const freqs = data.map((d) => d.frequency).filter((f) => f > 0)
  const freqMin = Math.max(50, Math.min(...freqs) * 0.8)
  const freqMax = Math.min(1200, Math.max(...freqs) * 1.2)
  const timeMin = data[0].time
  const timeMax = data[data.length - 1].time
  const timeRange = timeMax - timeMin || 1

  function freqToY(f: number): number {
    // 对数刻度: 对频率取log，更符合听觉感知
    const logMin = Math.log2(freqMin)
    const logMax = Math.log2(freqMax)
    const logF = Math.log2(Math.max(f, freqMin))
    return padding.top + plotH * (1 - (logF - logMin) / (logMax - logMin))
  }

  function timeToX(t: number): number {
    return padding.left + ((t - timeMin) / timeRange) * plotW
  }

  // 绘制网格
  ctx.strokeStyle = 'rgba(148, 163, 184, 0.15)'
  ctx.lineWidth = 1

  // 水平网格线 (频率参考)
  const refFreqs = [100, 200, 300, 400, 600, 800, 1000]
  for (const f of refFreqs) {
    if (f < freqMin || f > freqMax) continue
    const y = freqToY(f)
    ctx.beginPath()
    ctx.moveTo(padding.left, y)
    ctx.lineTo(padding.left + plotW, y)
    ctx.stroke()

    // Y 轴标签
    ctx.fillStyle = '#94a3b8'
    ctx.font = '10px sans-serif'
    ctx.textAlign = 'right'
    ctx.fillText(`${f}Hz`, padding.left - 4, y + 3)
  }

  // 绘制音高曲线
  ctx.beginPath()
  ctx.strokeStyle = props.lineColor
  ctx.lineWidth = 2
  ctx.lineJoin = 'round'

  let started = false
  for (const point of data) {
    const x = timeToX(point.time)
    const y = freqToY(point.frequency)
    const alpha = point.confidence ?? 1

    if (!started) {
      ctx.beginPath()
      ctx.moveTo(x, y)
      started = true
    } else if (point.frequency <= 0) {
      // 断开: 非有声段
      ctx.stroke()
      started = false
    } else {
      ctx.globalAlpha = 0.3 + alpha * 0.7
      ctx.lineTo(x, y)
    }
  }
  ctx.globalAlpha = 1
  ctx.stroke()

  // 播放游标
  if (props.currentTime > 0) {
    const cx = timeToX(props.currentTime)
    ctx.beginPath()
    ctx.strokeStyle = props.cursorColor
    ctx.lineWidth = 2
    ctx.moveTo(cx, padding.top)
    ctx.lineTo(cx, padding.top + plotH)
    ctx.stroke()
  }
}

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return

  dpr = window.devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  canvas.width = rect.width * dpr
  canvas.height = props.height * dpr
  canvas.style.width = `${rect.width}px`
  canvas.style.height = `${props.height}px`

  const ctx = canvas.getContext('2d')
  if (ctx) ctx.scale(dpr, dpr)

  draw()
})

watch(
  () => [props.pitchData, props.currentTime],
  () => {
    draw()
  },
  { deep: true },
)
</script>

<template>
  <canvas
    ref="canvasRef"
    class="pitch-curve-canvas"
    :style="{ height: height + 'px' }"
    role="img"
    aria-label="音高曲线图"
  />
</template>

<style scoped>
.pitch-curve-canvas {
  width: 100%;
  border-radius: var(--el-border-radius-base);
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
}
</style>
