<script setup lang="ts">
/**
 * ProgressOverlay — 固定顶部分析进度条
 *
 * 在分析进行中显示，包含阶段信息和百分比
 */

defineProps<{
  visible: boolean
  percent: number
  stage?: string
  message?: string
}>()
</script>

<template>
  <Teleport to="body">
    <Transition name="progress-fade">
      <div v-if="visible" class="progress-overlay" role="progressbar" :aria-valuenow="Math.round(percent)" aria-valuemin="0" aria-valuemax="100">
        <div class="progress-content">
          <div class="progress-bar-container">
            <div
              class="progress-bar-fill"
              :style="{ width: Math.min(100, Math.max(0, percent)) + '%' }"
            />
          </div>
          <div class="progress-info">
            <span v-if="stage" class="progress-stage">{{ stage }}</span>
            <span class="progress-message">{{ message || '处理中...' }}</span>
            <span class="progress-percent">{{ Math.round(percent) }}%</span>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.progress-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 2000;
  background: var(--el-bg-color-overlay);
  border-bottom: 1px solid var(--el-border-color-lighter);
  backdrop-filter: blur(8px);
  padding: 8px 0;
}

.progress-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 16px;
}

.progress-bar-container {
  height: 4px;
  background: var(--el-border-color);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 6px;
}

.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--el-color-primary), var(--el-color-primary-light-3));
  border-radius: 2px;
  transition: width 0.4s ease;
}

.progress-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.progress-stage {
  font-weight: 600;
  color: var(--el-color-primary);
}

.progress-percent {
  margin-left: auto;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

/* 过渡动画 */
.progress-fade-enter-active,
.progress-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.progress-fade-enter-from,
.progress-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
