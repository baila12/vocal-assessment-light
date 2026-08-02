<script setup lang="ts">
/**
 * WaveformCanvas — 音频波形可视化组件 (v7.0.3)
 *
 * 使用 Web Audio API 解码音频并以 Canvas 渲染波形峰值图。
 * 支持播放游标联动 (currentTime prop)。
 */

import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'

const props = withDefaults(
  defineProps<{
    audioUrl: string
    currentTime?: number
    height?: number
    waveColor?: string
    cursorColor?: string
  }>(),
  {
    currentTime: 0,
    height: 80,
    waveColor: '#6366f1',
    cursorColor: '#ef4444',
  },
)

const canvasRef = ref<HTMLCanvasElement | null>(null)
const isLoading = ref(false)
const hasError = ref(false)

let peaks: number[] = []
let duration = 0
let audioContext: AudioContext | null = null

async function loadAndDecode(): Promise<void> {
  if (!props.audioUrl) return
  isLoading.value = true
  hasError.value = false

  try {
    const response = await fetch(props.audioUrl)
    if (!response.ok) throw new Error('Failed to fetch audio')
    const arrayBuffer = await response.arrayBuffer()

    audioContext = new AudioContext()
    const audioBuffer = await audioContext.decodeAudioData(arrayBuffer)

    const rawData = audioBuffer.getChannelData(0)
    duration = audioBuffer.duration

    // 生成峰值数据 (每像素采样一个窗口)
    const canvas = canvasRef.value
    if (!canvas) return

    const width = canvas.getBoundingClientRect().width
    const samplesPerPixel = Math.floor(rawData.length / width) || 1
    peaks = []

    for (let i = 0; i < width; i++) {
      let max = 0
      const start = i * samplesPerPixel
      const end = Math.min(start + samplesPerPixel, rawData.length)
      for (let j = start; j < end; j++) {
        const abs = Math.abs(rawData[j])
        if (abs > max) max = abs
      }
      peaks.push(max)
    }

    draw()
  } catch {
    hasError.value = true
  } finally {
    isLoading.value = false
    audioContext?.close()
    audioContext = null
  }
}

function draw(): void {
  const canvas = canvasRef.value
  if (!canvas || peaks.length === 0) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const dpr = window.devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  canvas.width = rect.width * dpr
  canvas.height = props.height * dpr
  canvas.style.width = `${rect.width}px`
  canvas.style.height = `${props.height}px`
  ctx.scale(dpr, dpr)

  const w = rect.width
  const h = props.height
  const midY = h / 2

  ctx.clearRect(0, 0, w, h)

  // 背景网格
  ctx.strokeStyle = 'rgba(148, 163, 184, 0.1)'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(0, midY)
  ctx.lineTo(w, midY)
  ctx.stroke()

  // 波形
  ctx.fillStyle = props.waveColor
  const barWidth = Math.max(1, w / peaks.length)
  for (let i = 0; i < peaks.length; i++) {
    const barH = peaks[i] * midY * 0.9
    ctx.fillRect(i * barWidth, midY - barH, barWidth - 0.5, barH * 2)
  }

  // 播放游标
  if (props.currentTime > 0 && duration > 0) {
    const cx = (props.currentTime / duration) * w
    ctx.beginPath()
    ctx.strokeStyle = props.cursorColor
    ctx.lineWidth = 2
    ctx.moveTo(cx, 0)
    ctx.lineTo(cx, h)
    ctx.stroke()
  }
}

onMounted(() => {
  loadAndDecode()
})

onBeforeUnmount(() => {
  audioContext?.close()
})

watch(() => props.audioUrl, () => {
  peaks = []
  duration = 0
  loadAndDecode()
})

watch(() => props.currentTime, () => {
  if (peaks.length > 0) draw()
})
</script>

<template>
  <div class="waveform-container">
    <div v-if="isLoading" class="waveform-loading">加载波形中...</div>
    <div v-else-if="hasError" class="waveform-error"><el-icon><WarningFilled /></el-icon> 波形加载失败</div>
    <canvas
      ref="canvasRef"
      class="waveform-canvas"
      :style="{ height: height + 'px' }"
      role="img"
      aria-label="音频波形图"
    />
  </div>
</template>

<style scoped>
.waveform-container {
  position: relative;
  min-height: 40px;
}

.waveform-canvas {
  width: 100%;
  border-radius: var(--el-border-radius-base);
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
}

.waveform-loading,
.waveform-error {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.waveform-error {
  color: var(--el-color-warning);
}
</style>
