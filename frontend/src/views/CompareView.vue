<script setup lang="ts">
/**
 * CompareView — 对比分析页
 *
 * 双文件上传 (标准音频 + 用户音频) → DTW 对比评分
 * v7.0: 修复 v6.3 无法两侧都上传、字段名不匹配等已知问题
 */

import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Aim,
  Microphone,
  CircleCheckFilled,
  InfoFilled,
  CaretRight,
  VideoPause,
  Camera,
} from '@element-plus/icons-vue'
import { useGsap } from '@/composables/useGsap'
import { apiClient } from '@/api/client'
import { useSongMatchStore } from '@/stores/songMatch.store'
import { useSongsStore } from '@/stores/songs.store'
import { matchColor } from '@/utils/colors'
import type { MatchCandidate } from '@/types/api'
import FileUploader from '@/components/FileUploader.vue'
import PitchComparisonCanvas from '@/components/PitchComparisonCanvas.vue'
import {
  PLAYBACK_RATES,
  DEFAULT_PLAYBACK_RATE,
  advancePlayback,
  clampSeek,
  isShortAudio,
} from '@/utils/pitchPlayback'
import { alignPitchCurves } from '@/utils/pitchDeviation'
import { computeDeviationStats, excludeLowAlignmentFrames } from '@/utils/pitchStats'
import { computeHeatmapSegments, type HeatmapSegment } from '@/utils/pitchHeatmap'
import { createFpsMonitor } from '@/utils/pitchFps'
import { mapKeyboardAction } from '@/utils/pitchKeyboard'
import { downloadCanvasPng, formatTimestamp } from '@/utils/pitchScreenshot'
import type { PitchPoint, DeviationFrame, LowAlignmentSegment } from '@/types/pitch'

// ---- 状态 ----
const standardFile = ref<File | null>(null)
const userFile = ref<File | null>(null)
const isComparing = ref(false)
const compareResult = ref<any>(null)
const errorMsg = ref<string | null>(null)

// ---- v7.14: 自动匹配标准歌曲 (上传录音 → 候选列表 → 一键 DTW 对比) ----
const songMatchStore = useSongMatchStore()
const songsStore = useSongsStore()

// ---- Phase 5: 双轨叠加分析 (从 /api/v1/compare 响应映射的音高曲线) ----
/** /api/v1/compare 响应中的音高曲线段 (snake_case, 映射为前端 camelCase) */
interface ComparePitchPayload {
  standard_pitch?: PitchPoint[]
  user_pitch?: PitchPoint[]
  low_alignment_segments?: Array<{ start: number; end: number; avg_confidence: number }>
}

const standardPitchData = ref<PitchPoint[]>([])
const userPitchData = ref<PitchPoint[]>([])
const lowAlignmentSegments = ref<LowAlignmentSegment[]>([])

/** 播放/分析游标状态 */
const currentTime = ref(0)
const isPlaying = ref(false)
const playbackRate = ref<number>(DEFAULT_PLAYBACK_RATE)
const showReference = ref(true)
const isPerformanceMode = ref(false)
const showThumbnail = computed(() => !isShortAudio(totalDuration.value))
const fpsMonitor = createFpsMonitor()
const canvasHost = ref<HTMLElement | null>(null)
let playbackTimer: ReturnType<typeof setInterval> | null = null
let fpsRafId: number | null = null
let fpsLastTick: number | null = null

/** 背景/停顿间隙 >1s 视为暂停 (切 Tab 等) — 重置低帧率连段, 防止恢复瞬间误降级 */
const FPS_PAUSE_GAP_MS = 1000
/** 偏差热力图桶数 — 全时长粒度 */
const HEATMAP_BUCKETS = 48

// ---- GSAP 入场动画 ----
const compareContainer = ref<HTMLElement | null>(null)
const { slideInLeft, slideInRight, enterFrom } = useGsap(compareContainer)

onMounted(() => {
  if (!compareContainer.value) return
  // 左面板 (标准音频) 从左侧滑入
  slideInLeft('.upload-panel:first-child', { delay: 0.1 })
  // 右面板 (用户音频) 从右侧滑入
  slideInRight('.upload-panel:last-child', { delay: 0.2 })
  // 操作按钮区域
  enterFrom('.action-bar', { y: 16, delay: 0.3 })
  // Phase 5: 键盘快捷键 + FPS 监控 (画布挂载时独立 rAF loop)
  window.addEventListener('keydown', onWindowKeydown)
  startFpsLoop()
})

onBeforeUnmount(() => {
  window.removeEventListener('keydown', onWindowKeydown)
  stopFpsLoop()
  stopPlayback()
  // ctx.revert() handled by useGsap
})

// ---- 计算属性 ----
const canCompare = computed(
  () => standardFile.value !== null && userFile.value !== null && !isComparing,
)
const standardName = computed(() => standardFile.value?.name ?? '')
const userName = computed(() => userFile.value?.name ?? '')

// ---- v7.14: 自动匹配计算属性 ----
/** 上传了录音且不在匹配中 → 可触发自动匹配 */
const canAutoMatch = computed(
  () => userFile.value !== null && !songMatchStore.isMatching,
)
/** 已选中候选歌曲 + 已上传录音 → 可一键对比 */
const canAutoCompare = computed(
  () => userFile.value !== null && songMatchStore.selectedSongId !== null,
)
/** 无匹配回退文案 (透传后端 fallback_reason) */
const autoMatchFallbackText = computed(() => {
  const reason = songMatchStore.fallbackReason
  if (!reason) return ''
  const reasonMap: Record<string, string> = {
    no_match: '未匹配到足够相似的歌曲，可继续使用下方手动对比或绝对评分',
    no_profiles: '歌曲库暂无特征数据，请先在歌曲库完成特征预计算',
    audio_too_short: '录音过短，无法稳定匹配，请换一段更长的演唱',
    timeout: '匹配超时，请重试或使用下方手动对比',
  }
  return reasonMap[reason] || `匹配未成功 (${reason})，可继续手动对比`
})

/** 置信度 → 展示百分比 */
function pct(v: number): string {
  return `${Math.round((v ?? 0) * 100)}%`
}

/** 置信度 → 标签色 (≥0.7 高 / ≥0.6 中 / <0.6 低) */
function confidenceTagType(c: number): 'success' | 'warning' | 'danger' {
  if (c >= 0.7) return 'success'
  if (c >= 0.6) return 'warning'
  return 'danger'
}

/** 是否有音高数据可分析 — 双轨叠加区展示开关 */
const hasPitchData = computed(
  () => userPitchData.value.length > 0 || standardPitchData.value.length > 0,
)

/** 总时长 — 两曲线最大时间 (播放/热力图/缩略条共用) */
const totalDuration = computed(() => {
  const times = [...standardPitchData.value, ...userPitchData.value].map((d) => d.time)
  return times.length ? Math.max(...times) : 0
})

/** 对齐偏差帧 — 有标准曲线时逐帧着色 (前端时间戳对齐, 复用 SingView 同款) */
const deviationFrames = computed<DeviationFrame[]>(() =>
  standardPitchData.value.length > 0
    ? alignPitchCurves(userPitchData.value, standardPitchData.value)
    : [],
)

/** 剔除低对齐段后的偏差统计 — 满足 "DTW 未对齐段落: 统计排除跑调率" */
const deviationStats = computed(() =>
  computeDeviationStats(excludeLowAlignmentFrames(deviationFrames.value, lowAlignmentSegments.value)),
)

/** 是否存在有声偏差帧 — 全无声时统计面板降级为空态 */
const hasVoicedFrames = computed(() => deviationFrames.value.some((f) => !f.isSilent))

/** 底部偏差热力图段 — 全时长分桶, 低对齐段置灰 */
const heatmapSegments = computed<readonly HeatmapSegment[]>(() =>
  computeHeatmapSegments(deviationFrames.value, totalDuration.value, HEATMAP_BUCKETS, lowAlignmentSegments.value),
)

const currentTimeLabel = computed(() => formatTimestamp(currentTime.value))
const totalDurationLabel = computed(() => formatTimestamp(totalDuration.value))

// ---- 文件处理 ----
function resetAnalysis(): void {
  stopPlayback()
  compareResult.value = null
  errorMsg.value = null
  standardPitchData.value = []
  userPitchData.value = []
  lowAlignmentSegments.value = []
  currentTime.value = 0
  showReference.value = true
  isPerformanceMode.value = false
  fpsMonitor.restoreQualityMode()
}

function onStandardFile(file: File): void {
  standardFile.value = file
  resetAnalysis()
}

function onUserFile(file: File): void {
  userFile.value = file
  // v7.14: 更换录音 → 重置自动匹配结果 (候选/选中/对比结果失效)
  songMatchStore.clearMatch()
  resetAnalysis()
}

function clearAll(): void {
  standardFile.value = null
  userFile.value = null
  songMatchStore.clearMatch()
  resetAnalysis()
}

// ---- DTW 对比 ----
async function startCompare(): Promise<void> {
  if (!standardFile.value || !userFile.value) return

  isComparing.value = true
  errorMsg.value = null
  compareResult.value = null
  // 重试时先清空旧曲线/低对齐数据 — 避免失败后残留曲线而评分隐藏 (状态不一致)
  standardPitchData.value = []
  userPitchData.value = []
  lowAlignmentSegments.value = []

  const formData = new FormData()
  // 注意: v7.0 已统一字段名 standard_file / user_file
  formData.append('standard_file', standardFile.value)
  formData.append('user_file', userFile.value)

  try {
    const response = await apiClient.upload<{
      success: boolean
      data: {
        score: number
        level: string
        pitch_match_rate: number
        rhythm_match_rate: number
        avg_cents_error: number
        diagnosis: string[]
        standard_pitch?: PitchPoint[]
        user_pitch?: PitchPoint[]
        low_alignment_segments?: Array<{ start: number; end: number; avg_confidence: number }>
      }
    }>('/api/v1/compare', formData)

    if (response.success) {
      compareResult.value = response.data
      // Phase 5: 映射后端音高曲线 (snake_case → camelCase); 空数组优雅降级 (提取失败仍显示评分)
      const pitch = response.data as unknown as ComparePitchPayload
      standardPitchData.value = pitch.standard_pitch ?? []
      userPitchData.value = pitch.user_pitch ?? []
      lowAlignmentSegments.value = (pitch.low_alignment_segments ?? []).map((seg) => ({
        start: seg.start,
        end: seg.end,
        avgConfidence: seg.avg_confidence,
      }))
      ElMessage.success('对比分析完成')
    } else {
      throw new Error('对比失败')
    }
  } catch (e) {
    const msg = (e as Error).message || '对比分析失败'
    errorMsg.value = msg
    ElMessage.error(msg)
  } finally {
    isComparing.value = false
  }
}

// ---- v7.14: 自动匹配 — 上传录音 → 候选 → 一键对比 ----

/** 上传录音自动匹配标准歌曲 — 命中时自动选中最佳候选 */
async function startAutoMatch(): Promise<void> {
  if (!userFile.value) return
  errorMsg.value = null
  await songMatchStore.matchAudio(userFile.value)
  if (songMatchStore.matchedSong) {
    ElMessage.success(`已匹配: ${songMatchStore.matchedSong.title}`)
  } else if (songMatchStore.fallbackReason) {
    ElMessage.warning('未匹配到足够相似的歌曲，可手动对比')
  }
}

/** 点击候选歌曲 → 选中 (作为对比标准) */
function onSelectCandidate(candidate: MatchCandidate): void {
  songMatchStore.selectCandidate(candidate.song_id)
}

/** 与选中的标准歌曲 DTW 对比 — 复用 Phase 5 双轨叠加 (标准参考音高 + 用户录音音高) */
async function startAutoCompare(): Promise<void> {
  const songId = songMatchStore.selectedSongId
  if (!userFile.value || !songId) return

  isComparing.value = true
  errorMsg.value = null
  compareResult.value = null
  standardPitchData.value = []
  userPitchData.value = []
  lowAlignmentSegments.value = []

  try {
    const summary = await songMatchStore.compareWithSelected(userFile.value)
    compareResult.value = summary
    // 双轨叠加: 标准参考音高 (歌曲库) + 用户录音音高 (extract-pitch);
    // 各自失败降级为空数组 (提取失败仍显示评分, 对齐手动对比行为)
    const [stdPitch, usrPitch] = await Promise.all([
      songsStore.fetchSongPitch(songId),
      songMatchStore.fetchUserPitch(userFile.value),
    ])
    standardPitchData.value = stdPitch
    userPitchData.value = usrPitch
    lowAlignmentSegments.value = []
    ElMessage.success('对比分析完成')
  } catch (e) {
    const msg = (e as Error).message || '对比分析失败'
    errorMsg.value = msg
    ElMessage.error(msg)
  } finally {
    isComparing.value = false
  }
}

// ---- Phase 5: 播放控制 (复用 SingView 的 advancePlayback 节奏) ----
function stopPlayback(): void {
  if (playbackTimer) {
    clearInterval(playbackTimer)
    playbackTimer = null
  }
  isPlaying.value = false
}

/** 播放/暂停 — 100ms 推进游标 (不中断显示模式切换) */
function togglePlayback(): void {
  if (!hasPitchData.value) return
  if (isPlaying.value) {
    stopPlayback()
    return
  }
  isPlaying.value = true
  if (currentTime.value >= totalDuration.value) currentTime.value = 0
  playbackTimer = setInterval(() => {
    currentTime.value = advancePlayback({
      current: currentTime.value,
      dt: 0.1,
      rate: playbackRate.value,
      duration: totalDuration.value,
    })
    if (currentTime.value >= totalDuration.value) stopPlayback()
  }, 100)
}

/** 画布点击/进度条跳转 */
function onSeek(time: number): void {
  currentTime.value = clampSeek(time, totalDuration.value)
}

/** 缩略导航条 seek — 全时长比例跳转 */
function onThumbnailSeek(time: number): void {
  currentTime.value = clampSeek(time, totalDuration.value)
}

/** 快捷键步进 ±5s */
function seekBy(delta: number): void {
  currentTime.value = clampSeek(currentTime.value + delta, totalDuration.value)
}

// ---- Phase 5: 显示模式 / 截图 ----
/** 显示模式切换 — 不中断播放 (feature: "切换显示模式 不中断播放") */
function setDisplayMode(mode: 'userOnly' | 'dual'): void {
  showReference.value = mode === 'dual'
}

function toggleReference(): void {
  showReference.value = !showReference.value
}

/** 截图导出 — 画布 DPR 原分辨率 + 时间戳水印 */
function takeScreenshot(): void {
  const canvas = canvasHost.value?.querySelector('canvas') ?? null
  downloadCanvasPng(canvas, currentTime.value, totalDuration.value)
}

// ---- Phase 5: FPS 监控循环 (低性能设备降级) ----
function startFpsLoop(): void {
  stopFpsLoop()
  const tick = (): void => {
    const now = performance.now()
    // 后台恢复/长时间停顿: 仅重置时间基准 (不清降级状态, 已降级设备保持降级),
    // 防止把切 Tab 的间隙误计为持续低帧率连段 (resetTime 后 dtMs 从 0 起算)
    if (fpsLastTick !== null && now - fpsLastTick > FPS_PAUSE_GAP_MS) {
      fpsMonitor.resetTime(now)
    }
    fpsLastTick = now
    const state = fpsMonitor.recordFrame(now)
    // 仅画布实际展示时应用自动降级 (空闲/上传阶段不降级)
    if (hasPitchData.value && state.isAutoDegraded) isPerformanceMode.value = true
    fpsRafId = requestAnimationFrame(tick)
  }
  fpsRafId = requestAnimationFrame(tick)
}

function stopFpsLoop(): void {
  if (fpsRafId !== null) cancelAnimationFrame(fpsRafId)
  fpsRafId = null
}

/** 手动切回画质模式 (性能指示器 closable) */
function restoreQualityMode(): void {
  isPerformanceMode.value = false
  fpsMonitor.restoreQualityMode()
}

// ---- Phase 5: 键盘快捷键 ----
function onWindowKeydown(e: KeyboardEvent): void {
  if (!hasPitchData.value) return
  const action = mapKeyboardAction(e)
  if (action === null) return
  // 画布自身处理方向键 (±1s/±5s, a11y) — 窗口层跳过, 避免双重 seek
  if (
    (action === 'seekBack' || action === 'seekForward') &&
    e.target instanceof Element &&
    e.target.closest('canvas')
  ) {
    return
  }
  e.preventDefault()
  switch (action) {
    case 'playPause':
      togglePlayback()
      break
    case 'seekBack':
      seekBy(-5)
      break
    case 'seekForward':
      seekBy(5)
      break
    case 'toggleReference':
      toggleReference()
      break
    case 'takeScreenshot':
      takeScreenshot()
      break
    case 'modeUserOnly':
      setDisplayMode('userOnly')
      break
    case 'modeDualCurve':
      setDisplayMode('dual')
      break
  }
}

// ---- 结果展示辅助 (使用 @/utils/colors 共享工具) ----
</script>

<template>
  <div ref="compareContainer" class="compare-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title">对比分析</h2>
      <p class="page-desc">上传标准音频与你的演唱录音，获取 DTW 对比评分</p>
    </div>

    <!-- v7.14: 自动匹配标准歌曲 — 上传录音 → 候选 → 一键对比 -->
    <section class="auto-match" data-test="auto-match-section">
      <div class="auto-match-header">
        <h3 class="section-title">自动匹配标准歌曲</h3>
        <el-tag size="small" type="success" effect="light">v7.14</el-tag>
      </div>
      <p class="auto-match-desc">
        在下方「我的演唱」上传录音后，点击匹配即可从歌曲库识别最相近的标准歌曲，一键进入 DTW 对比。
      </p>

      <div class="auto-match-actions">
        <el-button
          type="primary"
          plain
          :icon="Aim"
          :loading="songMatchStore.isMatching"
          :disabled="!canAutoMatch"
          data-test="auto-match-run"
          @click="startAutoMatch"
        >
          {{ userFile ? '匹配当前录音' : '请先上传录音' }}
        </el-button>
        <span v-if="!userFile" class="auto-match-hint">先在下方「我的演唱」面板上传演唱录音</span>
      </div>

      <!-- 无匹配回退提示 -->
      <el-alert
        v-if="songMatchStore.fallbackReason"
        :title="autoMatchFallbackText"
        type="warning"
        show-icon
        class="auto-match-alert"
        data-test="auto-match-fallback"
      />

      <!-- 命中最佳匹配 -->
      <div v-if="songMatchStore.matchedSong" class="match-badge" data-test="auto-match-hit">
        <el-icon color="var(--el-color-success)"><CircleCheckFilled /></el-icon>
        <span>
          已匹配 <strong>{{ songMatchStore.matchedSong.title }}</strong> ·
          {{ songMatchStore.matchedSong.artist }} (置信度
          {{ pct(songMatchStore.matchedSong.confidence) }})
        </span>
      </div>

      <!-- Top-N 候选列表 -->
      <div v-if="songMatchStore.candidates.length" class="candidate-list" data-test="candidate-list">
        <div
          v-for="c in songMatchStore.candidates"
          :key="c.song_id"
          class="candidate-item"
          :class="{ 'candidate-item--selected': c.song_id === songMatchStore.selectedSongId }"
          data-test="candidate-item"
          @click="onSelectCandidate(c)"
        >
          <div class="candidate-main">
            <span class="candidate-title">{{ c.title }}</span>
            <span class="candidate-artist">{{ c.artist }}</span>
          </div>
          <div class="candidate-meta">
            <el-tag size="small" :type="confidenceTagType(c.confidence)">{{ pct(c.confidence) }}</el-tag>
            <span class="candidate-bpm">BPM 差 {{ c.bpm_diff }}</span>
            <span v-if="c.key_diff_semitones" class="candidate-key">调性差 {{ c.key_diff_semitones }} 半音</span>
          </div>
        </div>
      </div>

      <!-- 一键对比 -->
      <div v-if="canAutoCompare" class="auto-match-actions">
        <el-button
          type="primary"
          size="large"
          :loading="isComparing"
          data-test="auto-match-compare"
          @click="startAutoCompare"
        >
          与选中歌曲对比
        </el-button>
      </div>
    </section>

    <!-- 双文件上传区域 -->
    <div class="upload-dual">
      <div class="upload-panel">
        <div class="panel-header">
          <el-icon :size="20" color="var(--el-color-primary)"><Aim /></el-icon>
          <span>标准音频</span>
        </div>
        <FileUploader
          @file-selected="onStandardFile"
          @error="(msg: string) => ElMessage.warning(msg)"
        />
        <div v-if="standardFile" class="selected-file">
          <el-icon><CircleCheckFilled /></el-icon>
          <span>{{ standardName }}</span>
        </div>
      </div>

      <div class="divider-vs">
        <el-tag type="info" effect="dark" round>VS</el-tag>
      </div>

      <div class="upload-panel">
        <div class="panel-header">
          <el-icon :size="20" color="var(--el-color-success)"><Microphone /></el-icon>
          <span>我的演唱</span>
        </div>
        <FileUploader
          @file-selected="onUserFile"
          @error="(msg: string) => ElMessage.warning(msg)"
        />
        <div v-if="userFile" class="selected-file">
          <el-icon><CircleCheckFilled /></el-icon>
          <span>{{ userName }}</span>
        </div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="action-bar">
      <el-button
        type="primary"
        size="large"
        :disabled="!canCompare"
        :loading="isComparing"
        @click="startCompare"
      >
        {{ isComparing ? '分析中...' : '开始对比分析' }}
      </el-button>
      <el-button
        v-if="standardFile || userFile"
        size="large"
        @click="clearAll"
      >
        清除
      </el-button>
    </div>

    <!-- 错误提示 -->
    <el-alert
      v-if="errorMsg"
      :title="errorMsg"
      type="error"
      show-icon
      closable
      @close="errorMsg = null"
      class="error-alert"
    />

    <!-- 对比结果 -->
    <div v-if="compareResult" class="result-section">
      <h3 class="section-title">对比结果</h3>

      <div class="result-cards">
        <!-- 综合评分 -->
        <el-card shadow="hover" class="result-card">
          <div class="result-card-content">
            <span class="result-label">综合匹配评分</span>
            <span class="result-value-large" :style="{ color: matchColor(compareResult.score) }">
              {{ compareResult.score }}
            </span>
            <el-tag
              :type="compareResult.score >= 80 ? 'success' : compareResult.score >= 60 ? 'warning' : 'danger'"
            >
              {{ compareResult.level }}
            </el-tag>
          </div>
        </el-card>

        <!-- 音准匹配率 -->
        <el-card shadow="hover" class="result-card">
          <div class="result-card-content">
            <span class="result-label">音准匹配率</span>
            <span class="result-value" :style="{ color: matchColor(compareResult.pitch_match_rate) }">
              {{ compareResult.pitch_match_rate }}%
            </span>
            <el-progress
              :percentage="compareResult.pitch_match_rate"
              :color="compareResult.pitch_match_rate >= 80 ? '#22c55e' : compareResult.pitch_match_rate >= 60 ? '#f59e0b' : '#ef4444'"
              :stroke-width="6"
              :show-text="false"
            />
          </div>
        </el-card>

        <!-- 节奏匹配率 -->
        <el-card shadow="hover" class="result-card">
          <div class="result-card-content">
            <span class="result-label">节奏匹配率</span>
            <span class="result-value" :style="{ color: matchColor(compareResult.rhythm_match_rate) }">
              {{ compareResult.rhythm_match_rate }}%
            </span>
            <el-progress
              :percentage="compareResult.rhythm_match_rate"
              :color="compareResult.rhythm_match_rate >= 80 ? '#22c55e' : compareResult.rhythm_match_rate >= 60 ? '#f59e0b' : '#ef4444'"
              :stroke-width="6"
              :show-text="false"
            />
          </div>
        </el-card>

        <!-- 平均音分偏差 -->
        <el-card shadow="hover" class="result-card">
          <div class="result-card-content">
            <span class="result-label">平均音分偏差</span>
            <span class="result-value" :style="{ color: compareResult.avg_cents_error < 20 ? '#22c55e' : compareResult.avg_cents_error < 40 ? '#f59e0b' : '#ef4444' }">
              {{ compareResult.avg_cents_error }} cents
            </span>
          </div>
        </el-card>
      </div>

      <!-- 诊断建议 -->
      <div v-if="compareResult.diagnosis?.length > 0" class="diagnosis-section">
        <h4 class="diagnosis-title">诊断建议</h4>
        <ul class="diagnosis-list">
          <li v-for="(item, i) in compareResult.diagnosis" :key="i" class="diagnosis-item">
            <el-icon color="var(--el-color-primary)"><InfoFilled /></el-icon>
            <span>{{ item }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- Phase 5: 双轨叠加对比分析 (标准虚线 #6366f1 + 用户偏差着色 + 热力图 + 缩略条) -->
    <div v-if="hasPitchData" class="analysis-section" data-test="compare-analysis">
      <h3 class="section-title">音准曲线对比</h3>

      <!-- 操作栏: 显示模式 + 截图 + 性能指示器 + 时间 -->
      <div class="analysis-toolbar">
        <div class="analysis-buttons">
          <el-button
            size="small"
            :type="showReference ? 'primary' : 'default'"
            :disabled="standardPitchData.length === 0"
            data-test="mode-dual"
            @click="setDisplayMode('dual')"
          >
            显示对比
          </el-button>
          <el-button
            size="small"
            :type="!showReference ? 'primary' : 'default'"
            data-test="mode-user-only"
            @click="setDisplayMode('userOnly')"
          >
            仅显示用户曲线
          </el-button>
          <el-button size="small" :icon="Camera" data-test="compare-screenshot" @click="takeScreenshot">
            截图
          </el-button>
        </div>
        <div class="toolbar-right">
          <el-tag
            v-if="isPerformanceMode"
            type="warning"
            closable
            effect="dark"
            class="perf-tag"
            data-test="perf-mode-tag"
            @close="restoreQualityMode"
          >
            性能模式 (可手动关闭)
          </el-tag>
          <span class="time-label">{{ currentTimeLabel }} / {{ totalDurationLabel }}</span>
        </div>
      </div>

      <!-- 对比画布 -->
      <div ref="canvasHost" class="canvas-host">
        <PitchComparisonCanvas
          :user-pitch-data="userPitchData"
          :ref-pitch-data="showReference ? standardPitchData : []"
          :current-time="currentTime"
          :total-duration="totalDuration"
          :performance-mode="isPerformanceMode"
          :heatmap-segments="heatmapSegments"
          :low-alignment-segments="lowAlignmentSegments"
          :show-thumbnail="showThumbnail"
          :height="280"
          data-test="compare-pitch-canvas"
          @seek="onSeek"
          @thumbnail-seek="onThumbnailSeek"
        />
      </div>

      <!-- 播放控制 -->
      <div class="analysis-playback">
        <el-button
          size="small"
          type="primary"
          circle
          :icon="isPlaying ? VideoPause : CaretRight"
          :aria-label="isPlaying ? '暂停' : '播放'"
          data-test="compare-play-toggle"
          @click="togglePlayback"
        />
        <el-slider
          :model-value="currentTime"
          :min="0"
          :max="totalDuration"
          :step="0.1"
          class="seek-slider"
          data-test="compare-seek"
          @input="onSeek"
        />
        <el-select
          v-model="playbackRate"
          size="small"
          class="rate-select"
          aria-label="播放倍速"
          data-test="compare-rate"
        >
          <el-option v-for="rate in PLAYBACK_RATES" :key="rate" :label="`${rate}x`" :value="rate" />
        </el-select>
      </div>

      <!-- 偏差统计面板 (排除低置信度段落) -->
      <div v-if="hasVoicedFrames || lowAlignmentSegments.length > 0" class="deviation-panel" data-test="deviation-panel">
        <div class="deviation-pills">
          <span class="pill pill-accurate">精准率 {{ deviationStats.accuratePct }}%</span>
          <span class="pill pill-slight">略偏 {{ deviationStats.slightPct }}%</span>
          <span class="pill pill-out">跑调 {{ deviationStats.outOfTunePct }}%</span>
        </div>
        <span v-if="lowAlignmentSegments.length > 0" class="low-align-note" data-test="low-align-note">
          ⚠️ 已排除低置信度段落
        </span>
      </div>

      <!-- 快捷键提示 -->
      <p class="shortcut-hint">
        快捷键: Space 播放/暂停 · ←/→ ±5s · R 参考线 · S 截图 · 1 仅用户 · 2 双曲线
      </p>
    </div>
  </div>
</template>

<style scoped>
.compare-view {
  max-width: 900px;
  margin: 0 auto;
}

.page-header {
  text-align: center;
  margin-bottom: 32px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  margin: 0 0 8px;
}

.page-desc {
  color: var(--el-text-color-secondary);
  font-size: 14px;
  margin: 0;
}

/* ---- v7.14: 自动匹配标准歌曲 ---- */
.auto-match {
  padding: 20px;
  margin-bottom: 24px;
  border: 1px solid var(--el-border-color);
  border-radius: var(--el-border-radius-base);
  background: linear-gradient(180deg, var(--el-fill-color-blank), var(--el-fill-color-lighter));
}

.auto-match-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.auto-match-header .section-title {
  margin-bottom: 0;
}

.auto-match-desc {
  margin: 8px 0 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.auto-match-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.auto-match-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.auto-match-alert {
  margin-top: 16px;
}

.match-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 16px;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--el-color-success);
  background: var(--el-color-success-light-9);
  border-radius: var(--el-border-radius-base);
}

.match-badge strong {
  color: var(--el-color-success);
}

.candidate-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 16px;
}

.candidate-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.candidate-item:hover {
  border-color: var(--el-color-primary-light-5);
  background: var(--el-fill-color-light);
}

.candidate-item--selected {
  border-color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}

.candidate-main {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.candidate-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.candidate-artist {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.candidate-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  font-variant-numeric: tabular-nums;
}

/* 双上传区域 */
.upload-dual {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}

.upload-panel {
  flex: 1;
  min-width: 0;
}

.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-bottom: 12px;
}

.divider-vs {
  display: flex;
  align-items: center;
  padding-top: 40px;
  flex-shrink: 0;
}

.selected-file {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  margin-top: 8px;
  font-size: 13px;
  color: var(--el-color-success);
  background: var(--el-fill-color-light);
  border-radius: var(--el-border-radius-base);
}

.selected-file span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 操作栏 */
.action-bar {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-bottom: 24px;
}

.error-alert {
  margin-bottom: 20px;
}

/* 结果 */
.result-section {
  margin-top: 8px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 16px;
}

.result-cards {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}

.result-card-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.result-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.result-value-large {
  font-size: 42px;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.result-value {
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.diagnosis-section {
  margin-top: 20px;
}

.diagnosis-title {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 12px;
}

.diagnosis-list {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.diagnosis-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

/* ---- Phase 5: 双轨叠加分析 ---- */
.analysis-section {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid var(--el-border-color-lighter);
}

.analysis-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.analysis-buttons {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.perf-tag {
  margin-right: 4px;
}

.time-label {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  font-variant-numeric: tabular-nums;
}

.canvas-host {
  margin-bottom: 12px;
}

.analysis-playback {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.seek-slider {
  flex: 1;
}

.rate-select {
  width: 80px;
}

.deviation-panel {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
  padding: 12px 16px;
  background: var(--el-fill-color-light);
  border-radius: var(--el-border-radius-base);
  margin-bottom: 12px;
}

.deviation-pills {
  display: flex;
  gap: 16px;
}

.pill {
  font-size: 13px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.pill-accurate {
  color: #22c55e;
}

.pill-slight {
  color: #f59e0b;
}

.pill-out {
  color: #ef4444;
}

.low-align-note {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.shortcut-hint {
  margin: 0;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

@media (max-width: 767px) {
  .upload-dual {
    flex-direction: column;
  }
  .divider-vs {
    padding: 0;
    justify-content: center;
    width: 100%;
  }
  .result-cards {
    grid-template-columns: 1fr;
  }
  .compare-view {
    padding-bottom: 72px;
  }
}
</style>
