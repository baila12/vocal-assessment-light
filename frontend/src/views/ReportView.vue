<script setup lang="ts">
/**
 * ReportView — 评分报告页
 *
 * 六维雷达图 + 音高曲线 Canvas + 音频播放器 + 启发式标签 + 改进建议
 * 路由: /report/:id — 支持从历史记录恢复
 */

import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { WarningFilled, CircleCheck, Plus, Document } from '@element-plus/icons-vue'
import { useAssessmentStore } from '@/stores/assessment.store'
import { usePreferencesStore } from '@/stores/preferences.store'
import { useApi } from '@/composables/useApi'
import { apiClient, ApiError } from '@/api/client'
import { scoreColor } from '@/utils/colors'
import { useGsap } from '@/composables/useGsap'
import ScoreCard from '@/components/ScoreCard.vue'
import ScoreRadar from '@/components/ScoreRadar.vue'
import AudioPlayer from '@/components/AudioPlayer.vue'
import WaveformCanvas from '@/components/WaveformCanvas.vue'
import type { SixDimensionScores } from '@/types/score'
import type { AssessmentResult } from '@/types/api'

const router = useRouter()
const route = useRoute()
const assessment = useAssessmentStore()
const preferences = usePreferencesStore()
const { getAudioUrl } = useApi()

// ---- 状态 ----
const audioUrl = ref('')
const playbackTime = ref(0)

// ---- 计算属性 ----
const result = computed(() => assessment.currentResult)
const hasResult = computed(() => result.value !== null)
const isVoiceOk = computed(() => result.value?.is_voice !== false)

const scores = computed<SixDimensionScores>(() => {
  if (!result.value) {
    return { pitch: 0, rhythm: 0, breath: 0, technique: 0, muscle_strength: 0, artistry: 0 }
  }
  return result.value.scores
})

const heuristicDims = computed(() => result.value?.heuristic_dimensions ?? [])
const normalization = computed(() => result.value?.normalization)
const hasNormNote = computed(() => normalization.value?.applied && normalization.value?.note)

const scoreCards = computed(() => {
  const s = scores.value
  const h = heuristicDims.value
  return [
    { key: 'pitch', label: '音准', score: s.pitch, weight: 13, isHeuristic: false,
      subScores: {} },
    { key: 'rhythm', label: '节奏', score: s.rhythm, weight: 12, isHeuristic: false,
      subScores: {} },
    { key: 'breath', label: '气息', score: s.breath, weight: 22, isHeuristic: false,
      subScores: {} },
    { key: 'technique', label: '发声技术', score: s.technique, weight: 25, isHeuristic: false,
      subScores: {} },
    { key: 'muscle_strength', label: '肌肉力量', score: s.muscle_strength, weight: 15,
      isHeuristic: h.includes('muscle_strength'),
      subScores: {} },
    { key: 'artistry', label: '艺术表现', score: s.artistry, weight: 13, isHeuristic: false,
      subScores: {} },
  ]
})

const totalScoreColor = computed(() => scoreColor(result.value?.total_score ?? 0))

// ---- 从历史记录加载 ----
const loadingFromHistory = ref(false)

async function loadFromHistory(id: string): Promise<void> {
  loadingFromHistory.value = true
  try {
    const resp = await apiClient.get<{ success: boolean; record: AssessmentResult }>(
      `/api/v1/history/${id}`,
    )
    if (resp.success && resp.record) {
      assessment.setResult(resp.record)
      if (resp.record.filepath) {
        audioUrl.value = getAudioUrl(resp.record.filepath)
      }
    }
  } catch (e) {
    const msg = e instanceof ApiError ? e.message : '加载历史记录失败'
    ElMessage.error(msg)
  } finally {
    loadingFromHistory.value = false
  }
}

// ---- GSAP 动画 ----
const reportContainer = ref<HTMLElement | null>(null)
const { enterFrom, staggerIn, scaleIn } = useGsap(reportContainer)
let animPlayed = false

function playScoreReveal(): void {
  if (animPlayed || !reportContainer.value) return
  animPlayed = true

  // 等待 DOM 更新后播放动画
  nextTick(() => {
    if (!reportContainer.value) return
    // 总分区域弹入
    enterFrom('.score-hero', { y: 20, duration: 0.5 })
    // 雷达图缩放入场 (延迟 0.1s)
    scaleIn('.radar-section', { delay: 0.15 })
    // 六维卡片依次淡入
    staggerIn('.score-card-wrap', { y: 24, stagger: 0.08, delay: 0.2 })
    // 改进建议列表逐条滑入
    staggerIn('.advice-item', { x: -12, stagger: 0.06, delay: 0.4 })
    // 底部按钮区域
    enterFrom('.report-footer', { y: 16, delay: 0.6 })
  })
}

onBeforeUnmount(() => {
  animPlayed = false
})

// ---- 初始化 ----
onMounted(() => {
  const id = route.params.id as string | undefined
  if (id && !hasResult.value) {
    loadFromHistory(id)
  } else if (!hasResult.value) {
    ElMessage.warning('暂无分析结果，请先上传音频进行评估')
  }
  // 构建音频 URL
  if (result.value?.filepath) {
    audioUrl.value = getAudioUrl(result.value.filepath)
  }
  // 已有结果则播放动画
  if (hasResult.value) {
    playScoreReveal()
  }
})

watch(
  () => result.value?.filepath,
  (fp) => {
    if (fp) {
      audioUrl.value = getAudioUrl(fp)
    }
  },
)

// 数据从历史加载完成后触发动画
watch(hasResult, (now) => {
  if (now) playScoreReveal()
})

// ---- 导出报告 ----
const isExporting = ref(false)

async function exportReport(): Promise<void> {
  if (!result.value) return
  isExporting.value = true
  try {
    // 触发浏览器打印对话框 (本地桌面应用首选方案)
    // window.print() 在 Electron 中效果良好，支持保存为 PDF
    // 后端 POST /api/v1/report (PDF生成) 作为备选方案保留
    window.print()
    ElMessage.success('报告已发送到打印机')
  } catch {
    ElMessage.warning('导出失败，请尝试截图保存')
  } finally {
    isExporting.value = false
  }
}

// ---- 操作 ----
function goHome(): void {
  router.push('/')
}

function onTimeUpdate(time: number): void {
  playbackTime.value = time
}
</script>

<template>
  <div ref="reportContainer" class="report-view">
    <!-- 空状态 -->
    <div v-if="!hasResult" class="empty-state">
      <el-result icon="warning" title="暂无分析结果" sub-title="请先上传音频进行评估">
        <template #extra>
          <el-button type="primary" @click="goHome">返回首页</el-button>
        </template>
      </el-result>
    </div>

    <!-- 报告内容 -->
    <template v-else>
      <!-- 总分概览 -->
      <div class="score-hero">
        <div class="score-hero-left">
          <span class="total-label">综合评分</span>
          <div class="total-score-row">
            <span class="total-score" :style="{ color: totalScoreColor }">
              {{ result?.total_score }}
            </span>
            <span class="total-unit">分</span>
          </div>
          <div class="total-meta">
            <el-tag
              :color="totalScoreColor"
              size="large"
              effect="dark"
              class="level-tag"
            >
              {{ result?.level }} ({{ result?.grade }})
            </el-tag>
            <el-tag v-if="!isVoiceOk" type="danger" size="large" effect="dark">
              非人声
            </el-tag>
            <el-tag
              v-if="result?.timbre_adjustment && result.timbre_adjustment !== 0"
              :type="result.timbre_adjustment > 0 ? 'success' : 'warning'"
              size="large"
              effect="plain"
            >
              音色{{ result.timbre_adjustment > 0 ? '+' : '' }}{{ result.timbre_adjustment }}
            </el-tag>
          </div>
        </div>
        <div class="score-hero-right">
          <el-tag type="info" size="small">
            {{ result?.mode === 'professional' ? '专业评估' : '快速评估' }}
          </el-tag>
        </div>
      </div>

      <!-- 六维雷达图 -->
      <div class="radar-section">
        <h3 class="section-title">六维评分雷达图</h3>
        <ScoreRadar :scores="scores" :heuristic-dimensions="heuristicDims" />
        <p v-if="heuristicDims.length > 0" class="heuristic-note">
          <el-icon><WarningFilled /></el-icon>
          标记为 <el-tag type="warning" size="small" effect="plain">估算值</el-tag> 的维度基于麦克风音频的代理指标估算，非直接生理测量。点击维度卡片查看详情。
        </p>
        <p v-if="hasNormNote" class="heuristic-note">
          <el-icon><WarningFilled /></el-icon>
          {{ normalization?.note }}
        </p>
      </div>

      <!-- 六维评分卡片 -->
      <div class="cards-section">
        <h3 class="section-title">各维度详情</h3>
        <div class="cards-grid">
          <div v-for="card in scoreCards" :key="card.key" class="score-card-wrap">
            <ScoreCard
              :label="card.label"
              :score="card.score"
              :weight="card.weight"
              :is-heuristic="card.isHeuristic"
              :sub-scores="card.subScores"
            />
          </div>
        </div>
      </div>

      <!-- 音频回放 + 波形可视化 -->
      <div v-if="audioUrl" class="audio-section">
        <h3 class="section-title">音频回放</h3>
        <WaveformCanvas
          :audio-url="audioUrl"
          :current-time="playbackTime"
          :height="80"
        />
        <AudioPlayer
          class="audio-player"
          :audio-url="audioUrl"
          :auto-play="preferences.autoPlay"
          @time-update="onTimeUpdate"
        />
      </div>

      <!-- 改进建议 -->
      <div v-if="result?.advice && result.advice.length > 0" class="advice-section">
        <h3 class="section-title">改进建议</h3>
        <el-card shadow="never">
          <ul class="advice-list">
            <li v-for="(item, i) in result.advice" :key="i" class="advice-item">
              <el-icon color="var(--el-color-primary)"><CircleCheck /></el-icon>
              <span>{{ item }}</span>
            </li>
          </ul>
        </el-card>
      </div>

      <!-- 底部操作 -->
      <div class="report-footer">
        <el-button :icon="Plus" @click="goHome">新分析</el-button>
        <el-button type="primary" :icon="Document" :loading="isExporting" @click="exportReport">
          导出报告
        </el-button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.report-view {
  max-width: 800px;
  margin: 0 auto;
}

.empty-state {
  padding: 80px 0;
}

/* 总分区域 */
.score-hero {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  padding: 24px 0;
  margin-bottom: 32px;
  border-bottom: 2px solid var(--el-border-color-lighter);
}

.total-label {
  font-size: 15px;
  color: var(--el-text-color-secondary);
  margin-bottom: 4px;
  display: block;
}

.total-score-row {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.total-score {
  font-size: 64px;
  font-weight: 800;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  letter-spacing: -2px;
}

.total-unit {
  font-size: 18px;
  color: var(--el-text-color-secondary);
}

.total-meta {
  display: flex;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}

/* 区块标题 */
.section-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  margin: 0 0 16px;
}

/* 雷达图 */
.radar-section {
  margin-bottom: 40px;
}

.heuristic-note {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 8px;
  justify-content: center;
}

/* 评分卡片网格 */
.cards-section {
  margin-bottom: 40px;
}

.cards-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

/* 音频 */
.audio-section {
  margin-bottom: 40px;
}

.audio-player {
  margin-top: 8px;
}

/* 建议 */
.advice-section {
  margin-bottom: 40px;
}

.advice-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.advice-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  font-size: 14px;
  color: var(--el-text-color-regular);
  line-height: 1.6;
}

.advice-item .el-icon {
  margin-top: 2px;
  flex-shrink: 0;
}

/* 底部 */
.report-footer {
  display: flex;
  justify-content: center;
  gap: 12px;
  padding-bottom: 48px;
}

@media (max-width: 767px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }
  .total-score {
    font-size: 48px;
  }
  .report-view {
    padding-bottom: 72px;
  }
}

/* 打印样式 — 隐藏导航和按钮, 优化报告排版 */
@media print {
  .report-footer,
  .top-nav,
  .bottom-nav {
    display: none !important;
  }
  .report-view {
    padding: 0;
    max-width: 100%;
  }
  .cards-grid {
    break-inside: avoid;
  }
  .score-hero {
    break-after: avoid;
  }
  .radar-section,
  .cards-section,
  .advice-section {
    break-inside: avoid;
    margin-bottom: 16px;
  }
  .total-score {
    font-size: 48px;
  }
}
</style>
