<script setup lang="ts">
/**
 * SingView — 实时演唱页 (最高风险页面)
 *
 * 功能 (v7.13): AudioWorklet 重采样 + WebSocket 流式评分 +
 *   PitchComparisonCanvas 实时偏差着色对比 (v7.13 P1 参考线 + P2 全功能视口) +
 *   录音后回放控制 (播放/暂停/拖拽/倍速/A-B 循环)
 *
 * ⚠️ 清理法 (防内存泄露):
 *   1. stopReplay() — 回放定时器
 *   2. audioManager.stop()
 *   3. 清除 elapsedTimer
 *   4. wsManager.close()
 *   5. window.__audioCleanup() fallback
 */

import { ref, computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type UploadFile } from 'element-plus'
import { Microphone, VideoPause, CaretRight, Headset, ArrowRight, Upload } from '@element-plus/icons-vue'
import { useGsap } from '@/composables/useGsap'
import { useWebSocket } from '@/composables/useWebSocket'
import { useWsDisconnectGuard } from '@/composables/useWsDisconnectGuard'
import { useAudioContext } from '@/composables/useAudioContext'
import { useSongsStore } from '@/stores/songs.store'
import { apiClient, ApiError } from '@/api/client'
import { scoreColor } from '@/utils/colors'
import PitchComparisonCanvas from '@/components/PitchComparisonCanvas.vue'
import { PLAYBACK_RATES, DEFAULT_PLAYBACK_RATE, advancePlayback, clampSeek, wrapInABLoop } from '@/utils/pitchPlayback'
import type { ABLoopRange } from '@/utils/pitchPlayback'
import { alignPitchCurves, DEVIATION_COLORS } from '@/utils/pitchDeviation'
import { computeDeviationStats, computePitchRange } from '@/utils/pitchStats'
import type { SongRecord, SongDetailResponse, SongCompareData } from '@/types/api'
import type { PitchPoint } from '@/types/pitch'
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

// ---- 参考音高 (v7.13: 选歌录音参考线) ----
const refPitchData = ref<PitchPoint[]>([])
const refPitchLoading = ref(false)

// ---- 选歌后上传录音对比 (v7.13) ----
const compareResult = ref<SongCompareData | null>(null)
const compareLoading = ref(false)

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
  } else {
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

  // v7.13: 加载参考音高 (参考线叠加数据源, store 缓存避免重复请求)
  if (selectedSong.value) {
    refPitchData.value = []
    refPitchLoading.value = true
    try {
      refPitchData.value = await songsStore.fetchSongPitch(id)
    } catch {
      refPitchData.value = []
    } finally {
      refPitchLoading.value = false
    }
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
      refPitchData.value = []
      compareResult.value = null
      loadSongCandidates()
    }
  },
  { immediate: true },
)

// ---- GSAP 录音脉冲动画 ----
const singContainer = ref<HTMLElement | null>(null)
const recordBtn = ref<HTMLElement | null>(null)
const { pulse, enterFrom, scaleIn } = useGsap(singContainer)
let pulseTween: gsap.core.Tween | null = null

// ---- 状态 ----
const isConnected = ref(false)
const isSinging = ref(false)
/** v7.15 H-B15: WS 断连反馈 — 录音中断连时的常驻告警横幅 */
const wsDisconnected = ref(false)

// v7.15 H-B15: WS 断连守卫 — 连接状态同步 + 录音中断连自动停止录音并明确告知
// (初始未连接 / 显式 close 不触发; 仅"连接建立后中途断开"触发)
useWsDisconnectGuard(wsManager.isConnected, isConnected, () => {
  if (isSinging.value) {
    isSinging.value = false
    audioManager.stop()
    stopReplay()
    wsDisconnected.value = true
    ElMessage.error('连接已断开，录音已自动停止')
  }
})

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
const pitchHistory = ref<Array<{ time: number; freq: number; conf: number }>>([])
const partialScore = ref<{ pitch?: number; rhythm?: number; progress: number } | null>(null)
const finalResult = ref<any>(null)
const qualityWarning = ref<string | null>(null)
const sessionId = ref('')
const elapsedTime = ref(0)
/** 录音起始壁钟 (performance.now) — live 时钟基准, 10Hz 浮点推进 (Phase 3 圆点平滑淡出) */
const singStartWall = ref(0)

// ---- 回放控制 (v7.13 Phase 2: 偏差着色 + 播放控制) ----
const isReplaying = ref(false)
const playbackRate = ref<number>(DEFAULT_PLAYBACK_RATE)
const replayTime = ref(0)
const abLoop = ref<ABLoopRange | null>(null)
let replayTimer: ReturnType<typeof setInterval> | null = null

/** 用户音高曲线 (PitchPoint[] 供 PitchComparisonCanvas) — 低置信度帧透传 */
const userPitchPoints = computed<PitchPoint[]>(() =>
  pitchHistory.value.map((h) => ({
    time: h.time,
    frequency: h.freq,
    confidence: h.conf,
  })),
)

// ---- 回放统计 (v7.13 Phase 4: 播放结束/回放中显示精准/略偏/跑调 + 最高/最低音) ----
/** 是否有参考音高 (与 Canvas hasReference 判定一致) */
const hasRefPitch = computed(() => refPitchData.value.length > 0)

/**
 * 对齐偏差帧 — 有参考时逐帧对齐 (Canvas 内部同一逻辑, 供统计面板复用)。
 * 有意与 Canvas 各自调用一次 alignPitchCurves (重复对齐, 而非共享可变缓存):
 * align 为 O(n log m) 二分查找, 数百帧开销可忽略; 组件保持自包含便于 Phase 5 复用。
 */
const deviationFrames = computed(() =>
  hasRefPitch.value ? alignPitchCurves(userPitchPoints.value, refPitchData.value) : [],
)

/** 是否存在有声偏差帧 — 全无声时统计面板降级为空态 (避免误导性的 0%/0%/0%) */
const hasVoicedFrames = computed(() => deviationFrames.value.some((f) => !f.isSilent))

/** 偏差统计 — "精准率 X% | 略偏 Y% | 跑调 Z%" (分母为有声帧) */
const deviationStats = computed(() => computeDeviationStats(deviationFrames.value))

/** 音域范围 — 无参考时标注 "最高音 / 最低音" */
const pitchRange = computed(() => computePitchRange(userPitchPoints.value))

/** 总时长 — 参考曲线与用户曲线的最大时间 (回放游标上限) */
const totalDuration = computed(() => {
  const times = [...refPitchData.value, ...userPitchPoints.value].map((d) => d.time)
  return times.length ? Math.max(...times) : 0
})

/** 录音数据前沿 — WS 音高帧最大时间 (分数秒, 0.032s 粒度) */
const liveDataNow = computed<number>(() =>
  pitchHistory.value.length ? Math.max(...pitchHistory.value.map((h) => h.time)) : 0,
)

/**
 * 当前展示位置 — 回放中用 replayTime; 录音中 live 时钟与数据前沿取大:
 *   数据前沿保证新点立即可见 (不再被整数刻度截断), 壁钟保证圆点按真实时间连续淡出
 */
const displayTime = computed(() => {
  if (isReplaying.value) return replayTime.value
  if (isSinging.value) return Math.max(elapsedTime.value, liveDataNow.value)
  return elapsedTime.value
})

/** 录音计时器 — 10Hz 浮点 (0.5s 淡出窗口 ~5 次采样, 与回放游标 100ms 节奏一致) */
let elapsedTimer: ReturnType<typeof setInterval> | null = null

// ---- 辅助 ----
function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

// ---- 连接 WebSocket ----
async function initConnection(): Promise<void> {
  try {
    await wsManager.connect()
    // v7.15 H-B15: UI 连接状态由 useWsDisconnectGuard 单点同步 (含断连回落)
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
    wsDisconnected.value = false
    elapsedTime.value = 0
    singStartWall.value = performance.now()
    stopReplay()

    // 1. 发送 start 控制消息 (v7.12: 携带参考歌曲 song_id)
    wsManager.sendControl(
      'start',
      selectedSong.value ? { song_id: selectedSong.value.id } : undefined,
    )

    // 2. 开始录音 + AudioWorklet
    await audioManager.start((pcm: Float32Array) => {
      wsManager.sendPcm(pcm)
    })

    // 3. 开始录音 (Canvas 由 PitchComparisonCanvas 组件响应式渲染)
    isSinging.value = true
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
  audioManager.stop()
  wsManager.sendControl('stop')
}

// ---- 回放控制 (v7.13 Phase 2) ----
function stopReplay(): void {
  if (replayTimer) {
    clearInterval(replayTimer)
    replayTimer = null
  }
  isReplaying.value = false
  abLoop.value = null
}

/** 播放/暂停 — 录音结束后查看偏差着色曲线回放 */
function toggleReplay(): void {
  if (isSinging.value) return
  if (isReplaying.value) {
    stopReplay()
    return
  }
  // 开始回放: 每 100ms 推进 (10fps 游标平滑), dt 细分使 A-B 循环越界 ≤0.15s (无缝)
  isReplaying.value = true
  if (replayTime.value >= totalDuration.value) replayTime.value = 0
  replayTimer = setInterval(() => {
    const next = advancePlayback({
      current: replayTime.value,
      dt: 0.1,
      rate: playbackRate.value,
      duration: totalDuration.value,
    })
    replayTime.value = next
    // A-B 循环: 越过 B 点回绕到 A
    if (abLoop.value) replayTime.value = wrapInABLoop(replayTime.value, abLoop.value)
    if (replayTime.value >= totalDuration.value) {
      stopReplay()
    }
  }, 100)
}

/** 拖拽/点击跳转 — 画布 seek 事件 + 进度条 */
function onSeek(time: number): void {
  if (isSinging.value) return
  replayTime.value = clampSeek(time, totalDuration.value)
}

/** A-B 循环切换: 第 1 次设起点 A → 第 2 次设终点 B (B>A 激活) → 第 3 次清除 */
function toggleABLoop(): void {
  if (!abLoop.value) {
    abLoop.value = { a: replayTime.value, b: replayTime.value }
    ElMessage.info(`循环起点 A: ${formatElapsed(replayTime.value)}`)
    return
  }
  if (abLoop.value.b <= abLoop.value.a) {
    // 设置终点 B — 需大于起点
    if (replayTime.value <= abLoop.value.a) {
      ElMessage.warning('循环终点需大于起点，已清除循环')
      abLoop.value = null
      return
    }
    abLoop.value = { a: abLoop.value.a, b: replayTime.value }
    ElMessage.info(
      `A-B 循环: ${formatElapsed(abLoop.value.a)} - ${formatElapsed(abLoop.value.b)}`,
    )
    return
  }
  abLoop.value = null
  ElMessage.info('已清除 A-B 循环')
}

// ---- 选歌后上传已有录音 → DTW 对比 (v7.13, el-upload) ----
async function onUploadRecording(uploadFile: UploadFile): Promise<void> {
  const file = uploadFile.raw
  if (!file || !selectedSong.value) return

  compareLoading.value = true
  compareResult.value = null
  try {
    const formData = new FormData()
    formData.append('user_file', file)
    formData.append('style', selectedSong.value.metadata.style)
    compareResult.value = await songsStore.compareWithSong(selectedSong.value.id, formData)
    ElMessage.success('对比分析完成')
  } catch (err) {
    ElMessage.error(err instanceof Error ? err.message : '对比分析失败')
  } finally {
    compareLoading.value = false
  }
}

// ---- 再来一首 (v7.13: 录音完成后返回选歌状态) ----
function singAgain(): void {
  // 保留已完成的录音结果, 返回选歌状态
  clearSong()
}

// ---- GSAP 入场动画 (v7.13: 对比结果 / 再来一首) ----
watch(compareResult, (result) => {
  if (result) enterFrom('.compare-result', { y: 16, duration: 0.4 })
})

watch(finalResult, (result) => {
  if (result) scaleIn('.sing-again-row', { scale: 0.9, duration: 0.35 })
})

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
          // 不可变更新 (触发 PitchComparisonCanvas 重绘); 保持最近 2000 点
          const points: Array<{ time: number; freq: number; conf: number }> = []
          for (let i = 0; i < event.frequencies.length; i++) {
            points.push({
              time: event.times[i],
              freq: event.frequencies[i],
              conf: event.confidence?.[i] ?? 1,
            })
          }
          pitchHistory.value = [...pitchHistory.value, ...points].slice(-2000)
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
  initConnection().catch(() => { /* 错误已在 initConnection 内部处理 */ })

  elapsedTimer = setInterval(() => {
    if (isSinging.value) elapsedTime.value = (performance.now() - singStartWall.value) / 1000
  }, 100)
})

// ⚠️ 清理法 — 防止内存泄露
onBeforeUnmount(() => {
  stopReplay()
  // v7.15 H-B15: 先复位录音态, 避免 close() 触发断连守卫误报 "录音已自动停止"
  isSinging.value = false
  audioManager.stop()
  if (elapsedTimer) {
    clearInterval(elapsedTimer)
    elapsedTimer = null
  }
  wsManager.close()
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

    <!-- 选歌状态 (v7.12: 参考歌曲; v7.13: 参考音高 + 上传录音) -->
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
          <el-tag v-if="refPitchLoading" size="small" type="warning" effect="plain">
            参考音高加载中…
          </el-tag>
        </div>
        <div class="selected-song-actions">
          <el-upload
            :auto-upload="false"
            :show-file-list="false"
            accept="audio/*"
            data-test="upload-recording"
            :on-change="onUploadRecording"
          >
            <el-button
              size="small"
              :icon="Upload"
              :loading="compareLoading"
              data-test="upload-recording-btn"
            >
              上传已有录音
            </el-button>
          </el-upload>
          <el-button size="small" text type="primary" @click="clearSong">取消选择</el-button>
        </div>
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

    <!-- 实时音高对比 Canvas (v7.13 Phase 2 回放: 偏差着色/滚动窗口/播放游标; Phase 3 录音中实时圆点) -->
    <div class="canvas-container">
      <PitchComparisonCanvas
        :user-pitch-data="userPitchPoints"
        :ref-pitch-data="refPitchData"
        :current-time="displayTime"
        :total-duration="totalDuration"
        :ab-loop="abLoop"
        :live-mode="isSinging"
        :height="240"
        data-test="pitch-canvas"
        @seek="onSeek"
      />
    </div>

    <!-- 回放控制 (录音结束后) -->
    <div
      v-if="!isSinging && userPitchPoints.length > 1"
      class="playback-controls"
      data-test="playback-controls"
    >
      <el-button
        size="small"
        type="primary"
        :icon="isReplaying ? VideoPause : CaretRight"
        circle
        :aria-label="isReplaying ? '暂停回放' : '开始回放'"
        data-test="replay-toggle"
        @click="toggleReplay"
      />
      <el-slider
        :model-value="replayTime"
        :min="0"
        :max="totalDuration"
        :step="0.1"
        :show-tooltip="true"
        class="seek-slider"
        data-test="replay-seek"
        @input="onSeek"
      />
      <el-select
        v-model="playbackRate"
        size="small"
        class="rate-select"
        aria-label="播放倍速"
        data-test="replay-rate"
      >
        <el-option
          v-for="rate in PLAYBACK_RATES"
          :key="rate"
          :label="`${rate}x`"
          :value="rate"
        />
      </el-select>
      <el-button
        size="small"
        text
        :type="abLoop ? 'primary' : 'default'"
        :aria-label="'A-B 循环'"
        data-test="ab-loop-toggle"
        @click="toggleABLoop"
      >
        A-B
      </el-button>
    </div>

    <!-- 回放统计 (v7.13 Phase 4: 播放结束/回放中 — 有参考: 精准/略偏/跑调; 无参考: 最高/最低音) -->
    <div
      v-if="!isSinging && userPitchPoints.length > 1"
      class="replay-stats"
      data-test="replay-stats"
    >
      <el-card shadow="never" class="stats-card">
        <template #header><span>音准统计</span></template>
        <template v-if="hasRefPitch && hasVoicedFrames">
          <div class="stats-grid">
            <div class="stat-item" data-test="stat-accurate">
              <span class="stat-value" :style="{ color: DEVIATION_COLORS.accurate }">
                {{ deviationStats.accuratePct }}%
              </span>
              <span class="stat-label">精准</span>
            </div>
            <div class="stat-item" data-test="stat-slight">
              <span class="stat-value" :style="{ color: DEVIATION_COLORS.slightBias }">
                {{ deviationStats.slightPct }}%
              </span>
              <span class="stat-label">略偏</span>
            </div>
            <div class="stat-item" data-test="stat-out-of-tune">
              <span class="stat-value" :style="{ color: DEVIATION_COLORS.outOfTune }">
                {{ deviationStats.outOfTunePct }}%
              </span>
              <span class="stat-label">跑调</span>
            </div>
          </div>
        </template>
        <div v-else-if="pitchRange" class="stats-range" data-test="stat-pitch-range">
          <span>最高音: <b>{{ pitchRange.maxNote }}</b></span>
          <span>最低音: <b>{{ pitchRange.minNote }}</b></span>
        </div>
        <div v-else class="stats-empty">暂无有效音高数据</div>
      </el-card>
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
        {{ formatElapsed(displayTime) }}
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

    <!-- v7.15 H-B15: WS 断连反馈 — 录音中断连的常驻告警 (toast 可能被错过) -->
    <el-alert
      v-if="wsDisconnected"
      title="连接已断开，录音已自动停止"
      type="error"
      show-icon
      :closable="false"
      class="ws-disconnect-alert"
      data-test="ws-disconnect-alert"
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
      <!-- v7.14: 节奏无参考歌曲不可评 (后端 rhythm=null), 显示"分析中"而非假 0 分 -->
      <div v-if="partialScore.rhythm != null" class="partial-row">
        <span class="partial-label">节奏</span>
        <el-progress
          :percentage="partialScore.rhythm"
          :stroke-width="6"
          :show-text="true"
          class="partial-bar"
        />
      </div>
      <div v-else class="partial-row">
        <span class="partial-label">节奏</span>
        <span class="partial-pending">分析中…</span>
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
        <!-- v7.13: 再来一首 -->
        <div class="sing-again-row">
          <el-button
            type="primary"
            data-test="sing-again-btn"
            @click="singAgain"
          >
            再来一首
          </el-button>
        </div>
      </div>
    </Transition>

    <!-- 选歌后上传录音对比结果 (v7.13) -->
    <Transition name="fade">
      <div v-if="compareResult" class="compare-result" data-test="compare-result">
        <el-card shadow="hover">
          <template #header>
            <span>对比评分 — {{ selectedSong?.metadata.title }} {{ selectedSong?.metadata.artist }}</span>
          </template>
          <div class="compare-hero">
            <el-statistic
              title="综合评分"
              :value="compareResult.score"
              :precision="1"
              :value-style="{ color: scoreColor(compareResult.score), fontSize: '44px', fontWeight: 800 }"
            />
            <el-tag type="success" effect="light" size="small">{{ compareResult.level }}</el-tag>
          </div>
          <el-descriptions :column="3" size="small" border class="compare-metrics">
            <el-descriptions-item label="音准匹配率">{{ compareResult.pitch_match_rate }}%</el-descriptions-item>
            <el-descriptions-item label="节奏匹配率">{{ compareResult.rhythm_match_rate }}%</el-descriptions-item>
            <el-descriptions-item label="平均偏差">{{ compareResult.avg_cents_error }} 音分</el-descriptions-item>
          </el-descriptions>
          <div v-if="compareResult.diagnosis?.length" class="compare-diagnosis">
            <div v-for="(d, i) in compareResult.diagnosis" :key="i" class="compare-diagnosis-item">
              · {{ d }}
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
/* v7.13 Phase 2: 回放控制面板 */
.playback-controls { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; padding: 8px 12px; background: var(--el-bg-color-overlay); border: 1px solid var(--el-border-color-lighter); border-radius: var(--el-border-radius-base); }
/* v7.13 Phase 4: 回放统计面板 */
.replay-stats { margin-bottom: 20px; }
.replay-stats .stats-card { border-color: var(--el-border-color-lighter); }
.stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.stat-item { display: flex; flex-direction: column; align-items: center; gap: 2px; padding: 10px 4px; background: var(--el-fill-color-light); border-radius: var(--el-border-radius-small); }
.stat-value { font-size: 24px; font-weight: 800; line-height: 1; font-variant-numeric: tabular-nums; }
.stat-label { font-size: 12px; color: var(--el-text-color-secondary); }
.stats-range { display: flex; justify-content: center; gap: 24px; padding: 8px 0; font-size: 13px; color: var(--el-text-color-regular); }
.stats-range b { font-size: 15px; color: var(--el-text-color-primary); }
.stats-empty { text-align: center; font-size: 13px; color: var(--el-text-color-secondary); padding: 8px 0; }
.playback-controls .seek-slider { flex: 1; margin: 0 4px; }
.playback-controls .rate-select { width: 88px; }
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
.partial-pending { flex: 1; font-size: 13px; color: var(--el-text-color-placeholder); }
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
/* v7.13: 选歌录音增强 */
.selected-song-actions { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.sing-again-row { display: flex; justify-content: center; margin-top: 12px; }
.compare-result { margin-top: 8px; }
.compare-hero { display: flex; align-items: center; justify-content: center; gap: 12px; margin-bottom: 14px; }
.compare-metrics { margin-bottom: 12px; }
.compare-diagnosis { padding: 8px 12px; background: var(--el-fill-color-lighter); border-radius: var(--el-border-radius-small); }
.compare-diagnosis-item { font-size: 12px; color: var(--el-text-color-regular); margin: 2px 0; }
@media (max-width: 767px) { .sing-view { padding-bottom: 72px; } }
</style>
