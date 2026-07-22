<script setup lang="ts">
/**
 * AudioPlayer — 音频播放器组件
 *
 * 功能: play/pause, click-to-seek, time display, waveform (Phase 4+)
 * v7.0: 修复 v6.3 播放器不能拖动进度的已知问题
 */

import { ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps<{
  audioUrl: string
  autoPlay?: boolean
}>()

const emit = defineEmits<{
  (e: 'timeUpdate', time: number): void
  (e: 'ended'): void
}>()

const audioRef = ref<HTMLAudioElement | null>(null)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const progress = ref(0)
const isLoading = ref(true)
const hasError = ref(false)

function formatTime(seconds: number): string {
  if (!isFinite(seconds) || seconds < 0) return '00:00'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function togglePlay(): void {
  const audio = audioRef.value
  if (!audio) return

  if (audio.paused) {
    audio.play().catch(() => {
      hasError.value = true
    })
  } else {
    audio.pause()
  }
}

function seek(event: MouseEvent): void {
  const audio = audioRef.value
  if (!audio) return

  const target = event.currentTarget as HTMLElement
  const rect = target.getBoundingClientRect()
  const ratio = (event.clientX - rect.left) / rect.width
  audio.currentTime = ratio * audio.duration
}

function onTimeUpdate(): void {
  const audio = audioRef.value
  if (!audio) return

  currentTime.value = audio.currentTime
  if (audio.duration > 0) {
    progress.value = (audio.currentTime / audio.duration) * 100
  }
  emit('timeUpdate', audio.currentTime)
}

function onLoadedMetadata(): void {
  const audio = audioRef.value
  if (!audio) return

  duration.value = audio.duration
  isLoading.value = false
}

function onEnded(): void {
  isPlaying.value = false
  emit('ended')
}

function onPlay(): void {
  isPlaying.value = true
}

function onPause(): void {
  isPlaying.value = false
}

function onError(): void {
  hasError.value = true
  isLoading.value = false
}

watch(
  () => props.audioUrl,
  () => {
    isLoading.value = true
    hasError.value = false
    currentTime.value = 0
    duration.value = 0
    progress.value = 0
  },
)

onBeforeUnmount(() => {
  const audio = audioRef.value
  if (audio) {
    audio.pause()
    audio.src = ''
  }
})
</script>

<template>
  <div class="audio-player" :class="{ error: hasError }">
    <!-- 隐藏的 audio 元素 -->
    <audio
      ref="audioRef"
      :src="audioUrl"
      preload="metadata"
      @timeupdate="onTimeUpdate"
      @loadedmetadata="onLoadedMetadata"
      @ended="onEnded"
      @play="onPlay"
      @pause="onPause"
      @error="onError"
    />

    <div class="player-controls">
      <!-- Play/Pause 按钮 -->
      <el-button
        :icon="isPlaying ? 'VideoPause' : 'VideoPlay'"
        circle
        size="large"
        :disabled="hasError"
        @click="togglePlay"
        :aria-label="isPlaying ? '暂停' : '播放'"
      />

      <!-- 进度条 (click-to-seek) -->
      <div
        class="progress-bar"
        role="slider"
        :aria-valuenow="Math.round(progress)"
        aria-valuemin="0"
        aria-valuemax="100"
        @click="seek"
      >
        <div class="progress-track">
          <div
            class="progress-fill"
            :style="{ width: progress + '%' }"
          />
        </div>
      </div>

      <!-- 时间显示 -->
      <span class="time-display">
        {{ hasError ? '加载失败' : isLoading ? '加载中...' : `${formatTime(currentTime)} / ${formatTime(duration)}` }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.audio-player {
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  padding: 12px 16px;
}

.audio-player.error {
  border-color: var(--el-color-danger);
}

.player-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.progress-bar {
  flex: 1;
  cursor: pointer;
  padding: 8px 0;
}

.progress-track {
  height: 6px;
  background: var(--el-border-color);
  border-radius: 3px;
  overflow: hidden;
  transition: height 0.15s;
}

.progress-bar:hover .progress-track {
  height: 8px;
}

.progress-fill {
  height: 100%;
  background: var(--el-color-primary);
  border-radius: 3px;
  transition: width 0.1s linear;
}

.time-display {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  min-width: 100px;
  text-align: right;
}
</style>
