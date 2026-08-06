<script setup lang="ts">
/**
 * SingView — 实时演唱页 (最高风险页面)
 *
 * 功能: Canvas 实时音高绘制 + AudioWorklet 重采样 + WebSocket 流式评分
 *
 * ⚠️ 6 步清理法 (防内存泄露):
 *   1. cancelAnimationFrame
 *   2. audioContext.close()
 *   3. mediaStream.getTracks().forEach(stop)
 *   4. ws.close(1000)
 *   5. ctx.clearRect
 *   6. window.__audioCleanup() fallback
 */

import { ref, computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Microphone, VideoPause, Headset, ArrowRight } from '@element-plus/icons-vue'
import { useGsap } from '@/composables/useGsap'
import { useWebSocket } from '@/composables/useWebSocket'
import { useAudioContext } from '@/composables/useAudioContext'
import { useSongsStore } from '@/stores/songs.store'
import { apiClient, ApiError } from '@/api/client'
import { scoreColor } from '@/utils/colors'
import type { SongRecord, SongDetailResponse } from '@/types/api'
import type { WsEvent } from '@/composables/useWebSocket'

// ---- Composables ----
const wsManager = useWebSocket()
const audioManager = useAudioContext()
const route = useRoute()
const router = useRouter()
const songsStore = useSongsStore()

// ---- 选歌状态 (v7.12: 选歌录音 — 从曲库选择参考歌曲) ----
const selectedSong = ref<SongRecord | null>(null)
const songLoading = ref(false)
const songError = ref<string | null>(null)
const songId = computed(() => (route.params.songId as string | undefined) ?? '')

/** 加载曲库列表供选歌区展示 (无 songId 时) */
async function loadSongCandidates(): Promise<void> {
  try {
    if (songsStore.songs.length === 0) await songsStore.fetchSongs()
  } catch {
    // 曲库加载失败不阻塞演唱页
  }
}

/** 选择歌曲 → 路由跳转到 /sing/:songId (携带参考歌曲) */
function selectSong(song: SongRecord): void {
  if (isSinging.value) {
    ElMessage.warning('录音进行中，请先停止录音')
    return
  }
  router.push({ name: 'sing', params: { songId: song.id } })
}

/** 取消选择 → 回到 /sing (选歌区) */
function clearSong(): void {
  if (isSinging.value) {
    ElMessage.warning('录音进行中，请先停止录音')
    return
  }
  router.push({ name: 'sing' })
}

/** 按路由参数加载参考歌曲 */
async function loadSong(id: string): Promise<void> {
  // 优先从曲库 store 查找 (选歌区已加载的歌曲直接可用, 避免重复 API 请求)
  const fromStore = songsStore.songs.find((s) => s.id === id)
  if (fromStore) {
    selectedSong.value = fromStore
    return
  }
  songLoading.value = true
  songError.value = null
  selectedSong.value = null
  try {
    const json = await apiClient.get<SongDetailResponse>(`/api/v1/songs/${id}`)
    if (json.success && json.song) {
      selectedSong.value = json.song
    } else {
      songError.value = '歌曲不存在'
    }
  } catch (e) {
    songError.value = e instanceof ApiError ? e.message : '歌曲加载失败'
  } finally {
    songLoading.value = false
  }
}

watch(
  songId,
  (id) => {
    if (id) {
      loadSong(id)
    } else {
      selectedSong.value = null
      songError.value = null
      loadSongCandidates()
    }
  },
  { immediate: true },
)

// ---- GSAP 录音脉冲动画 ----
const singContainer = ref<HTMLElement | null>(null)
const recordBtn = ref<HTMLElement | null>(null)
const { pulse } = useGsap(singContainer)
let pulseTween: gsap.core.Tween | null = null

// ---- 状态 ----
const isConnected = ref(false)
const isSinging = ref(false)

// ---- GSAP 录音脉冲 (watch 必须在 isSinging 声明之后) ----
watch(isSinging, (singing) => {
  if (singing && recordBtn.value) {
    pulseTween = pulse(recordBtn.value, {
      scale: 1.05,
      duration: 0.6,
      repeat: -1,
      yoyo: true,
      ease: 'sine.inOut',
    })
  } else {
    pulseTween?.kill()
    pulseTween = null
    if (recordBtn.value) {
      import('gsap').then(({ gsap }) => {
        gsap.set(recordBtn.value!, { scale: 1 })
      })
    }
  }
})
const canvasRef = ref<HTMLCanvasElement | null>(null)
const pitchHistory = ref<Array<{ time: number; freq: number; conf: number }>>([])
const partialScore = ref<{ pitch?: number; rhythm?: number; progress: number } | null>(null)
const finalResult = ref<any>(null)
const qualityWarning = ref<string | null>(null)
const sessionId = ref('')
const elapsedTime = ref(0)

// ---- Canvas / 动画 ----
let animationId: number | null = null
let canvasCtx: CanvasRenderingContext2D | null = null
let elapsedTimer: ReturnType<typeof setInterval> | null = null

// ---- 录制 ----

// ---- 辅助 ----
function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

// ---- 连接 WebSocket ----
async function initConnection(): Promise<void> {
  try {
    await wsManager.connect()
    isConnected.value = true
  } catch {
    ElMessage.error('无法连接到评分引擎，请确认后端已启动')
  }
}

// ---- 开始演唱 ----
async function startSinging(): Promise<void> {
  try {
    if (!isConnected.value) {
      await initConnection()
      if (!isConnected.value) return
    }

    pitchHistory.value = []
    partialScore.value = null
    finalResult.value = null
    qualityWarning.value = null
    elapsedTime.value = 0

    // 1. 发送 start 控制消息 (v7.12: 携带参考歌曲 song_id)
    wsManager.sendControl(
      'start',
      selectedSong.value ? { song_id: selectedSong.value.id } : undefined,
    )

    // 2. 开始录音 + AudioWorklet
    await audioManager.start((pcm: Float32Array) => {
      wsManager.sendPcm(pcm)
    })

    // 3. 开始 Canvas 绘制循环
    isSinging.value = true
    drawLoop()
  } catch (e) {
    const msg = e instanceof Error ? e.message : '录音启动失败'
    ElMessage.error(`无法开始录音: ${msg}`)
    // 确保状态复位
    isSinging.value = false
    wsManager.sendControl('stop')
  }
}

// ---- 停止演唱 ----
function stopSinging(): void {
  isSinging.value = false

  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }

  audioManager.stop()
  wsManager.sendControl('stop')
}

// ---- Canvas 绘制 ----
function drawLoop(): void {
  if (!isSinging.value) return

  const canvas = canvasRef.value
  if (!canvas) {
    animationId = requestAnimationFrame(drawLoop)
    return
  }

  if (!canvasCtx) {
    canvasCtx = canvas.getContext('2d')
  }

  const ctx = canvasCtx!
  const { width, height } = canvas

  ctx.clearRect(0, 0, width, height)
  ctx.fillStyle = '#0f172a'
  ctx.fillRect(0, 0, width, height)

  // 网格线
  ctx.strokeStyle = 'rgba(148, 163, 184, 0.08)'
  ctx.lineWidth = 1
  for (let i = 0; i < 8; i++) {
    const y = (height / 8) * i
    ctx.beginPath()
    ctx.moveTo(0, y)
    ctx.lineTo(width, y)
    ctx.stroke()
  }

  // 音高曲线
  const history = pitchHistory.value
  if (history.length > 1) {
    ctx.beginPath()
    ctx.strokeStyle = '#6366f1'
    ctx.lineWidth = 2
    ctx.lineJoin = 'round'

    const maxTime = history[history.length - 1].time
    const minTime = Math.max(0, maxTime - 5)
    const timeRange = Math.max(maxTime - minTime, 1)

    let started = false
    for (const point of history) {
      if (point.freq <= 0) {
        if (started) { ctx.stroke(); started = false }
        continue
      }
      const x = ((point.time - minTime) / timeRange) * width
      const logFreq = Math.log2(Math.max(point.freq, 50))
      const y = height * (1 - (logFreq - Math.log2(50)) / (Math.log2(1200) - Math.log2(50)))
      const alpha = 0.3 + point.conf * 0.7

      if (!started) {
        ctx.beginPath()
        ctx.moveTo(x, Math.max(0, Math.min(height, y)))
        started = true
      } else {
        ctx.globalAlpha = alpha
        ctx.lineTo(x, Math.max(0, Math.min(height, y)))
      }
    }
    ctx.globalAlpha = 1
    ctx.stroke()
  }

  // 状态文字
  ctx.fillStyle = '#cbd5e1'
  ctx.font = '13px monospace'
  ctx.textAlign = 'left'
  ctx.fillText(formatElapsed(elapsedTime.value), 12, height - 12)

  if (partialScore.value) {
    ctx.textAlign = 'right'
    const ps = partialScore.value
    const text = `音准: ${ps.pitch ?? '--'} | 节奏: ${ps.rhythm ?? '--'} | 进度: ${Math.round(ps.progress * 100)}%`
    ctx.fillText(text, width - 12, height - 12)
  }

  animationId = requestAnimationFrame(drawLoop)
}

// ---- WebSocket 事件处理 ----
watch(
  () => wsManager.lastEvent.value,
  (event: WsEvent | null) => {
    if (!event) return

    switch (event.event) {
      case 'ready':
        sessionId.value = event.session_id || ''
        break
      case 'pitch_update':
        if (event.frequencies && event.times) {
          for (let i = 0; i < event.frequencies.length; i++) {
            pitchHistory.value.push({
              time: event.times[i],
              freq: event.frequencies[i],
              conf: event.confidence?.[i] ?? 1,
            })
          }
          // 保持最近 2000 个数据点 (~33s @ 60fps)
          if (pitchHistory.value.length > 2000) {
            pitchHistory.value = pitchHistory.value.slice(-2000)
          }
        }
        break
      case 'partial_score':
        partialScore.value = {
          pitch: event.pitch,
          rhythm: event.rhythm,
          progress: event.progress,
        }
        break
      case 'quality_warning':
        qualityWarning.value = event.message
        break
      case 'final_score':
        finalResult.value = event
        ElMessage.success(`评分完成: ${event.total} 分`)
        break
      case 'error':
        ElMessage.error(event.message || '评分出错')
        break
    }
  },
)

// ---- 初始化 ----
onMounted(() => {
  const canvas = canvasRef.value
  if (canvas) {
    const dpr = window.devicePixelRatio || 1
    const rect = canvas.getBoundingClientRect()
    canvas.width = rect.width * dpr
    canvas.height = 240 * dpr
    canvas.style.width = `${rect.width}px`
    canvas.style.height = '240px'
    const ctx = canvas.getContext('2d')
    if (ctx) ctx.scale(dpr, dpr)
  }

  initConnection().catch(() => { /* 错误已在 initConnection 内部处理 */ })

  elapsedTimer = setInterval(() => {
    if (isSinging.value) elapsedTime.value++
  }, 1000)
})

// ⚠️ 6 步清理法 — 防止内存泄露
onBeforeUnmount(() => {
  if (animationId) {
    cancelAnimationFrame(animationId)
    animationId = null
  }
  audioManager.stop()
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
  wsManager.close()
  if (canvasRef.value) {
    const ctx = canvasRef.value.getContext('2d')
    if (ctx) ctx.clearRect(0, 0, canvasRef.value.width, canvasRef.value.height)
  }
  if (window.__audioCleanup) {
    window.__audioCleanup()
  }
})
</script>

<template>
  <div ref="singContainer" class="sing-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title">实时演唱</h2>
      <div class="connection-status">
        <el-tag :type="isConnected ? 'success' : 'danger'" size="small" effect="light">
          {{ isConnected ? `已连接 (${sessionId || '...'})` : '未连接' }}
        </el-tag>
      </div>
    </div>

    <!-- 选歌状态 (v7.12: 参考歌曲) -->
    <div v-if="songId" class="song-selection" data-test="selected-song">
      <template v-if="selectedSong">
        <div class="selected-song-info">
          <el-icon :size="20" color="var(--el-color-primary)"><Headset /></el-icon>
          <span class="song-title">{{ selectedSong.metadata.title }}</span>
          <span class="song-artist">{{ selectedSong.metadata.artist }}</span>
          <el-tag size="small" effect="plain">{{ selectedSong.metadata.key }}</el-tag>
          <el-tag v-if="selectedSong.metadata.bpm" size="small" effect="plain">
            {{ selectedSong.metadata.bpm }} BPM
          </el-tag>
          <el-tag v-if="selectedSong.metadata.vocal_range" size="small" type="info" effect="plain">
            音域 {{ selectedSong.metadata.vocal_range }}
          </el-tag>
        </div>
        <el-button size="small" text type="primary" @click="clearSong">取消选择</el-button>
      </template>
      <div v-else-if="songLoading" class="song-status">加载歌曲中…</div>
      <div v-else class="song-status song-error">
        <span>{{ songError || '歌曲不存在' }}</span>
        <el-button size="small" text type="primary" @click="router.push('/songs')">返回曲库</el-button>
      </div>
    </div>

    <!-- 选歌区 (无 songId) -->
    <div v-else class="song-selection-area" data-test="song-selection-area">
      <div class="select-area-header">
        <h3 class="select-title">选择标准歌曲</h3>
        <span class="select-hint">请先选择一首标准歌曲作为演唱参考</span>
      </div>
      <div v-if="songsStore.hasSongs" class="song-candidate-list">
        <div
          v-for="s in songsStore.songs"
          :key="s.id"
          class="song-candidate"
          :data-test="`song-${s.id}`"
          @click="selectSong(s)"
        >
          <span class="cand-title">{{ s.metadata.title }}</span>
          <span class="cand-artist">{{ s.metadata.artist }}</span>
          <el-icon class="cand-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
      <div v-else-if="songsStore.songs.length === 0" class="empty-library">
        <el-empty description="曲库为空" :image-size="60">
          <el-button type="primary" size="small" @click="router.push('/songs')">
            前往曲库导入标准歌曲
          </el-button>
        </el-empty>
      </div>
    </div>

    <!-- 实时音高 Canvas -->
    <div class="canvas-container">
      <canvas
        ref="canvasRef"
        class="pitch-canvas"
        role="img"
        aria-label="实时音高显示"
        data-test="pitch-canvas"
      />
    </div>

    <!-- 演唱控制 -->
    <div class="controls-section">
      <el-button
        v-if="!isSinging"
        type="primary"
        size="large"
        :icon="Microphone"
        :disabled="!isConnected"
        circle
        ref="recordBtn"
        class="record-btn"
        data-test="record-btn"
        @click="startSinging"
        aria-label="开始演唱"
      />

      <el-button
        v-else
        type="danger"
        size="large"
        :icon="VideoPause"
        circle
        class="record-btn recording"
        data-test="record-btn-recording"
        @click="stopSinging"
        aria-label="停止演唱"
      />

      <div class="elapsed-display">
        {{ formatElapsed(elapsedTime) }}
      </div>
    </div>

    <!-- 质量警告 -->
    <el-alert
      v-if="qualityWarning"
      :title="qualityWarning"
      type="warning"
      show-icon
      :closable="false"
      class="warning-alert"
    />

    <!-- 实时评分预览 -->
    <div v-if="partialScore" class="partial-score" data-test="partial-score">
      <div class="partial-row">
        <span class="partial-label">音准</span>
        <el-progress
          :percentage="partialScore.pitch ?? 0"
          :stroke-width="6"
          :show-text="true"
          class="partial-bar"
        />
      </div>
      <div class="partial-row">
        <span class="partial-label">节奏</span>
        <el-progress
          :percentage="partialScore.rhythm ?? 0"
          :stroke-width="6"
          :show-text="true"
          class="partial-bar"
        />
      </div>
      <div class="partial-row">
        <span class="partial-label">进度</span>
        <el-progress
          :percentage="Math.round((partialScore.progress ?? 0) * 100)"
          :stroke-width="4"
          :show-text="true"
          class="partial-bar"
        />
      </div>
    </div>

    <!-- 最终评分结果 -->
    <Transition name="fade">
      <div v-if="finalResult" class="final-result">
        <el-card shadow="hover">
          <template #header><span>评分结果</span></template>
          <div class="final-score-hero">
            <span class="final-total" :style="{ color: scoreColor(finalResult.total) }">
              {{ finalResult.total }}
            </span>
            <span class="final-unit">分</span>
          </div>
          <div v-if="finalResult.scores" class="final-scores-grid">
            <div v-for="(val, key) in finalResult.scores" :key="key" class="final-dim">
              <span class="final-dim-label">{{ key }}</span>
              <span class="final-dim-value">{{ val }}</span>
            </div>
          </div>
        </el-card>
      </div>
    </Transition>

    <!-- 操作提示 -->
    <div v-if="!isSinging && !finalResult" class="tips">
      <el-alert title="使用说明" type="info" :closable="false" show-icon>
        <template #default>
          <ol>
            <li>确保麦克风已连接并授权</li>
            <li>点击录音按钮开始演唱 (无需选歌)</li>
            <li>演唱过程中会实时显示音高曲线</li>
            <li>点击停止按钮获取完整六维评分</li>
          </ol>
        </template>
      </el-alert>
    </div>
  </div>
</template>

<style scoped>
.sing-view { max-width: 640px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.page-title { font-size: 24px; font-weight: 700; margin: 0; }
.canvas-container { border-radius: var(--el-border-radius-base); overflow: hidden; margin-bottom: 20px; }
.pitch-canvas { width: 100%; height: 240px; display: block; }
.controls-section { display: flex; flex-direction: column; align-items: center; gap: 12px; margin-bottom: 24px; }
.record-btn { width: 72px !important; height: 72px !important; font-size: 28px !important; transition: transform 0.15s, box-shadow 0.15s; }
.record-btn:hover { transform: scale(1.05); }
.record-btn.recording { animation: pulse 1.5s infinite; box-shadow: 0 0 0 8px rgba(239, 68, 68, 0.25); }
@keyframes pulse { 0%, 100% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0.25); } 50% { box-shadow: 0 0 0 16px rgba(239, 68, 68, 0.08); } }
.elapsed-display { font-size: 28px; font-weight: 700; color: var(--el-text-color-primary); font-variant-numeric: tabular-nums; letter-spacing: 1px; }
.warning-alert { margin-bottom: 16px; }
.partial-score { display: flex; flex-direction: column; gap: 10px; padding: 16px; background: var(--el-bg-color-overlay); border: 1px solid var(--el-border-color-lighter); border-radius: var(--el-border-radius-base); margin-bottom: 20px; }
.partial-row { display: flex; align-items: center; gap: 12px; }
.partial-label { font-size: 13px; font-weight: 600; color: var(--el-text-color-secondary); min-width: 36px; }
.partial-bar { flex: 1; }
.final-result { margin-top: 8px; }
.final-score-hero { display: flex; align-items: baseline; justify-content: center; gap: 4px; margin-bottom: 16px; }
.final-total { font-size: 56px; font-weight: 800; line-height: 1; }
.final-unit { font-size: 18px; color: var(--el-text-color-secondary); }
.final-scores-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.final-dim { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 8px; background: var(--el-fill-color-light); border-radius: var(--el-border-radius-small); }
.final-dim-label { font-size: 11px; color: var(--el-text-color-secondary); }
.final-dim-value { font-size: 18px; font-weight: 700; color: var(--el-text-color-primary); }
.tips { margin-bottom: 24px; }
.tips ol { margin: 0; padding-left: 20px; }
.tips li { margin: 4px 0; font-size: 13px; color: var(--el-text-color-regular); }
/* v7.12: 选歌区 */
.song-selection { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 12px 16px; background: var(--el-bg-color-overlay); border: 1px solid var(--el-border-color-lighter); border-radius: var(--el-border-radius-base); margin-bottom: 16px; flex-wrap: wrap; }
.selected-song-info { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.selected-song-info .song-title { font-size: 15px; font-weight: 700; color: var(--el-text-color-primary); }
.selected-song-info .song-artist { font-size: 13px; color: var(--el-text-color-secondary); }
.song-status { font-size: 13px; color: var(--el-text-color-secondary); }
.song-error { display: flex; align-items: center; gap: 8px; color: var(--el-color-danger); }
.song-selection-area { padding: 14px 16px; background: var(--el-fill-color-lighter); border: 1px dashed var(--el-border-color); border-radius: var(--el-border-radius-base); margin-bottom: 16px; }
.select-area-header { display: flex; align-items: baseline; gap: 10px; margin-bottom: 10px; }
.select-title { font-size: 15px; font-weight: 600; margin: 0; }
.select-hint { font-size: 12px; color: var(--el-text-color-secondary); }
.song-candidate-list { display: flex; flex-direction: column; gap: 6px; max-height: 200px; overflow-y: auto; }
.song-candidate { display: flex; align-items: center; gap: 10px; padding: 8px 12px; background: var(--el-bg-color); border: 1px solid var(--el-border-color-lighter); border-radius: var(--el-border-radius-base); cursor: pointer; transition: border-color 0.2s, background 0.2s; }
.song-candidate:hover { border-color: var(--el-color-primary); background: var(--el-fill-color-light); }
.song-candidate .cand-title { font-size: 14px; font-weight: 600; }
.song-candidate .cand-artist { font-size: 12px; color: var(--el-text-color-secondary); }
.song-candidate .cand-arrow { margin-left: auto; color: var(--el-text-color-placeholder); }
.empty-library { padding: 4px 0; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s ease, transform 0.3s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(8px); }
@media (max-width: 767px) { .sing-view { padding-bottom: 72px; } }
</style>
