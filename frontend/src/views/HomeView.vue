<script setup lang="ts">
/**
 * HomeView — 首页: 上传评估 + 模式选择 + 设置抽屉 + 曲库抽屉
 *
 * v7.0 迁移: ElDrawer 替代独立设置/曲库页面
 * 设计原则: 首页是工作台入口，不是产品介绍页
 */

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Setting, Folder, Delete, VideoPlay, Microphone, DataAnalysis, Lightning, Aim, Document, Moon, Sunny } from '@element-plus/icons-vue'
import { useAssessmentStore } from '@/stores/assessment.store'
import { usePreferencesStore } from '@/stores/preferences.store'
import FileUploader from '@/components/FileUploader.vue'
import ProgressOverlay from '@/components/ProgressOverlay.vue'

const router = useRouter()
const assessment = useAssessmentStore()
const preferences = usePreferencesStore()

// ---- 状态 ----
const selectedFile = ref<File | null>(null)
const analysisMode = ref<'quick' | 'professional'>(preferences.evalMode)
const settingsVisible = ref(false)
const libraryVisible = ref(false)
const healthStatus = ref<string>('检查中...')
const healthVersion = ref<string>('')

// ---- 计算属性 ----
const canStart = computed(() => selectedFile.value !== null && !assessment.isAnalyzing)
const fileName = computed(() => selectedFile.value?.name ?? '')
const fileSize = computed(() => {
  if (!selectedFile.value) return ''
  const mb = selectedFile.value.size / (1024 * 1024)
  return mb < 1 ? `${(mb * 1024).toFixed(0)} KB` : `${mb.toFixed(1)} MB`
})

// ---- 健康检查 ----
async function checkHealth(): Promise<void> {
  try {
    const resp = await fetch(
      `${(window as any).BACKEND_URL || 'http://127.0.0.1:8000'}/health`,
    )
    const data = await resp.json()
    healthStatus.value = data.status === 'healthy' ? 'healthy' : 'unhealthy'
    healthVersion.value = data.version || ''
  } catch {
    healthStatus.value = '后端未启动'
  }
}

checkHealth()

// ---- 文件处理 ----
function onFileSelected(file: File): void {
  selectedFile.value = file
}

function clearFile(): void {
  selectedFile.value = null
}

// ---- 分析 ----
async function startAnalysis(): Promise<void> {
  if (!selectedFile.value) return

  preferences.setEvalMode(analysisMode.value)

  try {
    const result = await assessment.uploadAndAnalyze(
      selectedFile.value,
      analysisMode.value,
    )
    // 自动跳转到报告页
    if (preferences.autoNavigate) {
      router.push(`/report/${result.analysis_id}`)
    }
  } catch (e) {
    ElMessage.error((e as Error).message || '分析失败，请重试')
  }
}

// ---- 导航 ----
function goToCompare(): void {
  router.push('/compare')
}

function goToSing(): void {
  router.push('/sing')
}
</script>

<template>
  <div class="home-view">
    <ProgressOverlay
      :visible="assessment.isAnalyzing"
      :percent="assessment.progress.percent"
      :stage="assessment.progress.stage"
      :message="assessment.progress.message"
    />

    <!-- 顶部状态栏 -->
    <div class="status-bar">
      <div class="backend-status">
        <el-tag
          :type="healthStatus === 'healthy' ? 'success' : 'danger'"
          size="small"
          effect="light"
        >
          {{ healthStatus === 'healthy' ? `后端 v${healthVersion}` : healthStatus }}
        </el-tag>
      </div>
      <div class="status-actions">
        <el-button text circle :icon="Setting" @click="settingsVisible = true" aria-label="设置" />
        <el-button text circle :icon="Folder" @click="libraryVisible = true" aria-label="曲库" />
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="hero-section">
      <el-icon :size="56" color="var(--el-color-primary)">
        <Headset />
      </el-icon>
      <h1 class="hero-title">声乐评估</h1>
      <p class="hero-subtitle">上传你的演唱录音，获取专业级六维评分</p>
    </div>

    <!-- 上传区域 -->
    <div class="upload-section">
      <FileUploader
        :disabled="assessment.isAnalyzing"
        @file-selected="onFileSelected"
        @error="(msg: string) => ElMessage.warning(msg)"
      />

      <!-- 已选文件信息 -->
      <Transition name="fade">
        <div v-if="selectedFile" class="file-info">
          <div class="file-info-left">
            <el-icon><Document /></el-icon>
            <span class="file-name">{{ fileName }}</span>
            <el-tag size="small" type="info">{{ fileSize }}</el-tag>
          </div>
          <el-button text type="danger" :icon="Delete" size="small" @click="clearFile">
            移除
          </el-button>
        </div>
      </Transition>
    </div>

    <!-- 模式选择 -->
    <div class="mode-section">
      <el-radio-group
        v-model="analysisMode"
        :disabled="assessment.isAnalyzing"
        size="large"
        class="mode-group"
      >
        <el-radio-button value="quick">
          <el-icon><Lightning /></el-icon>
          快速评估
          <span class="mode-desc">~30s</span>
        </el-radio-button>
        <el-radio-button value="professional">
          <el-icon><Aim /></el-icon>
          专业评估
          <span class="mode-desc">2-5min</span>
        </el-radio-button>
      </el-radio-group>
    </div>

    <!-- 操作按钮 -->
    <div class="action-section">
      <el-button
        type="primary"
        size="large"
        :disabled="!canStart"
        :loading="assessment.isAnalyzing"
        :icon="VideoPlay"
        @click="startAnalysis"
      >
        {{ assessment.isAnalyzing ? '分析中...' : '开始分析' }}
      </el-button>
      <div class="secondary-actions">
        <el-button :icon="Microphone" @click="goToSing">
          实时演唱
        </el-button>
        <el-button :icon="DataAnalysis" @click="goToCompare">
          对比分析
        </el-button>
      </div>
    </div>

    <!-- 模式说明 -->
    <div class="mode-info">
      <el-alert
        v-if="analysisMode === 'quick'"
        title="快速评估"
        type="info"
        :closable="false"
        show-icon
      >
        <template #default>
          快速评分（五维基础 + 特征增强），适合日常练习快速反馈。不执行 Demucs 人声分离和深度学习模型。
        </template>
      </el-alert>
      <el-alert
        v-else
        title="专业评估"
        type="info"
        :closable="false"
        show-icon
      >
        <template #default>
          完整六维评分 + Demucs 人声分离 + 深度学习质量评估 + 逐句评分 + 音色分析。
          CPU 约 2-3 分钟，GPU 约 30-50 秒。
        </template>
      </el-alert>
    </div>

    <!-- 错误提示 -->
    <Transition name="fade">
      <el-alert
        v-if="assessment.error"
        :title="assessment.error"
        type="error"
        show-icon
        closable
        @close="assessment.error = null"
        class="error-alert"
      />
    </Transition>

    <!-- ====== 设置抽屉 ====== -->
    <el-drawer
      v-model="settingsVisible"
      title="设置"
      direction="rtl"
      size="360px"
    >
      <div class="drawer-section">
        <h3 class="drawer-section-title">外观</h3>
        <div class="setting-row">
          <span>主题</span>
          <el-switch
            :model-value="preferences.theme === 'dark'"
            inline-prompt
            :active-icon="Moon"
            :inactive-icon="Sunny"
            @change="preferences.toggleTheme()"
          />
        </div>
      </div>

      <el-divider />

      <div class="drawer-section">
        <h3 class="drawer-section-title">评估偏好</h3>
        <div class="setting-row">
          <span>默认模式</span>
          <el-radio-group
            :model-value="preferences.evalMode"
            size="small"
            @change="(val: string) => preferences.setEvalMode(val as 'quick' | 'professional')"
          >
            <el-radio-button value="quick" label="快速" />
            <el-radio-button value="professional" label="专业" />
          </el-radio-group>
        </div>
        <div class="setting-row">
          <span>自动跳转报告</span>
          <el-switch
            :model-value="preferences.autoNavigate"
            @change="preferences.setAutoNavigate"
          />
        </div>
        <div class="setting-row">
          <span>自动播放音频</span>
          <el-switch
            :model-value="preferences.autoPlay"
            @change="preferences.setAutoPlay"
          />
        </div>
      </div>

      <el-divider />

      <div class="drawer-section">
        <h3 class="drawer-section-title">数据管理</h3>
        <el-button text type="danger" :icon="Delete" @click="router.push('/history')">
          管理历史记录
        </el-button>
      </div>
    </el-drawer>

    <!-- ====== 曲库抽屉 ====== -->
    <el-drawer
      v-model="libraryVisible"
      title="标准曲库"
      direction="rtl"
      size="400px"
    >
      <div class="drawer-section">
        <p class="drawer-empty">
          曲库功能开发中 (Phase 4+)<br/>
          后续将支持浏览、搜索、导入标准音频
        </p>
      </div>
    </el-drawer>
  </div>
</template>

<style scoped>
.home-view {
  max-width: 640px;
  margin: 0 auto;
}

.status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.status-actions {
  display: flex;
  gap: 4px;
}

.hero-section {
  text-align: center;
  margin-bottom: 32px;
}

.hero-title {
  font-size: 32px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  margin: 12px 0 4px;
  letter-spacing: -1px;
}

.hero-subtitle {
  color: var(--el-text-color-secondary);
  font-size: 15px;
  margin: 0;
}

.upload-section {
  margin-bottom: 20px;
}

.file-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  margin-top: 8px;
  background: var(--el-fill-color-light);
  border-radius: var(--el-border-radius-base);
}

.file-info-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.file-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  max-width: 280px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mode-section {
  text-align: center;
  margin-bottom: 20px;
}

.mode-group {
  flex-wrap: wrap;
  justify-content: center;
}

.mode-group :deep(.el-radio-button__inner) {
  display: flex;
  align-items: center;
  gap: 6px;
}

.mode-desc {
  font-size: 11px;
  opacity: 0.7;
}

.action-section {
  text-align: center;
  margin-bottom: 24px;
}

.secondary-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  margin-top: 16px;
}

.mode-info {
  margin-bottom: 16px;
}

.error-alert {
  margin-bottom: 16px;
}

/* 抽屉样式 */
.drawer-section {
  padding: 0;
}

.drawer-section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin: 0 0 12px;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.drawer-empty {
  color: var(--el-text-color-placeholder);
  text-align: center;
  padding: 40px 0;
  line-height: 1.8;
}

/* 动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 响应式 */
@media (max-width: 767px) {
  .hero-title {
    font-size: 24px;
  }
  .home-view {
    padding-bottom: 72px; /* bottom nav spacing */
  }
}
</style>
