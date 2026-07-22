<script setup lang="ts">
/**
 * CompareView — 对比分析页
 *
 * 双文件上传 (标准音频 + 用户音频) → DTW 对比评分
 * v7.0: 修复 v6.3 无法两侧都上传、字段名不匹配等已知问题
 */

import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Aim, Microphone, CircleCheckFilled, InfoFilled } from '@element-plus/icons-vue'
import { apiClient } from '@/api/client'
import FileUploader from '@/components/FileUploader.vue'

// ---- 状态 ----
const standardFile = ref<File | null>(null)
const userFile = ref<File | null>(null)
const isComparing = ref(false)
const compareResult = ref<any>(null)
const errorMsg = ref<string | null>(null)

// ---- 计算属性 ----
const canCompare = computed(
  () => standardFile.value !== null && userFile.value !== null && !isComparing,
)
const standardName = computed(() => standardFile.value?.name ?? '')
const userName = computed(() => userFile.value?.name ?? '')

// ---- 文件处理 ----
function onStandardFile(file: File): void {
  standardFile.value = file
  compareResult.value = null
  errorMsg.value = null
}

function onUserFile(file: File): void {
  userFile.value = file
  compareResult.value = null
  errorMsg.value = null
}

function clearAll(): void {
  standardFile.value = null
  userFile.value = null
  compareResult.value = null
  errorMsg.value = null
}

// ---- DTW 对比 ----
async function startCompare(): Promise<void> {
  if (!standardFile.value || !userFile.value) return

  isComparing.value = true
  errorMsg.value = null
  compareResult.value = null

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
      }
    }>('/api/v1/compare', formData)

    if (response.success) {
      compareResult.value = response.data
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

// ---- 结果展示辅助 ----
function getScoreColor(score: number): string {
  if (score >= 80) return 'var(--el-color-success)'
  if (score >= 60) return 'var(--el-color-warning)'
  return 'var(--el-color-danger)'
}

function getMatchColor(rate: number): string {
  if (rate >= 80) return 'var(--el-color-success)'
  if (rate >= 60) return 'var(--el-color-warning)'
  return 'var(--el-color-danger)'
}
</script>

<template>
  <div class="compare-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title">对比分析</h2>
      <p class="page-desc">上传标准音频与你的演唱录音，获取 DTW 对比评分</p>
    </div>

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
            <span class="result-value-large" :style="{ color: getScoreColor(compareResult.score) }">
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
            <span class="result-value" :style="{ color: getMatchColor(compareResult.pitch_match_rate) }">
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
            <span class="result-value" :style="{ color: getMatchColor(compareResult.rhythm_match_rate) }">
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
