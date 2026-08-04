<!--
  ScoringWeightsPanel — 评分权重配置面板 (v7.11, scoring-config.feature)

  功能:
  - 风格预设选择 (流行/美声/民族/说唱/自定义)
  - 六维权重滑块 (0-50%, 实时校验总和=100%)
  - 自动归一化开关 (按比例缩放到 100%)
  - 对既有维度分数用当前权重重算总分 (纯前端, POST apply-weights)

  用法 (ReportView):
    <ScoringWeightsPanel
      :dimension-scores="scores"
      :timbre-adjustment="result.timbre_adjustment"
    />
-->
<template>
  <el-card shadow="never" class="scoring-weights-panel" data-test="scoring-weights-panel">
    <template #header>
      <div class="panel-header">
        <span class="panel-title">
          <el-icon><SetUp /></el-icon>
          评分权重
        </span>
        <el-tag
          v-if="store.isValid"
          type="success"
          size="small"
          effect="plain"
        >
          当前: {{ store.activePresetLabel }}
        </el-tag>
        <el-tag v-else type="danger" size="small" effect="plain">
          权重不合法 (总和 {{ Math.round(store.weightSum * 100) }}%)
        </el-tag>
      </div>
    </template>

    <div class="panel-body">
      <!-- 预设选择 -->
      <div class="preset-row">
        <el-radio-group
          v-model="store.selectedPreset"
          size="small"
          @change="onPresetChange"
        >
          <el-radio-button value="default">默认</el-radio-button>
          <el-radio-button
            v-for="p in store.presetsData?.presets ?? []"
            :key="p.name"
            :value="p.name"
          >
            {{ p.label }}
          </el-radio-button>
          <el-radio-button value="custom">自定义</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 权重滑块 -->
      <div v-if="isCustomMode" class="sliders">
        <div v-for="dim in DIMENSIONS" :key="dim.key" class="slider-row">
          <span class="slider-label">{{ dim.label }}</span>
          <el-slider
            v-model="store.customWeights[dim.key]"
            :min="0"
            :max="0.5"
            :step="0.01"
            :show-tooltip="true"
            @input="onSliderInput"
          />
          <span class="slider-value">{{ Math.round(store.customWeights[dim.key] * 100) }}%</span>
        </div>

        <div class="slider-sum">
          <span>总和</span>
          <el-tag
            :type="store.isValid ? 'success' : 'danger'"
            size="small"
          >
            {{ Math.round(store.weightSum * 100) }}%
          </el-tag>
          <span class="sum-hint" :class="{ invalid: !store.isValid }">
            {{ store.isValid ? '权重总和 100% ✓' : '需恰好为 100%' }}
          </span>
          <el-button
            size="small"
            text
            type="primary"
            class="normalize-btn"
            @click="store.autoNormalize"
          >
            自动归一化
          </el-button>
        </div>
      </div>

      <!-- 重算结果 -->
      <div class="recalc-row">
        <el-button
          type="primary"
          size="small"
          :loading="recalcLoading"
          :disabled="!store.isValid"
          @click="onRecalc"
        >
          用当前权重重算
        </el-button>
        <template v-if="recalcResult">
          <span class="recalc-total" :style="{ color: recalcResult.color }">
            {{ recalcResult.total_score }} 分
          </span>
          <span class="recalc-meta">
            {{ recalcResult.level }} ({{ recalcResult.grade }}) · {{ recalcResult.stars }}
          </span>
          <span v-if="delta !== null" class="recalc-delta" :class="delta >= 0 ? 'up' : 'down'">
            {{ delta >= 0 ? '+' : '' }}{{ delta.toFixed(1) }} vs 原总分
          </span>
        </template>
      </div>

      <p v-if="store.error" class="panel-error">{{ store.error }}</p>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useScoringStore } from '@/stores/scoring.store'
import type { ApplyWeightsData } from '@/types/api'

const props = defineProps<{
  /** 六维原始分数 {pitch..artistry} — 来自分析结果 */
  dimensionScores: Record<string, number>
  /** 原分析的音色调整值 (复用) */
  timbreAdjustment?: number
  /** 原总分 — 用于显示对比差值 */
  originalTotal?: number
}>()

const store = useScoringStore()
const recalcLoading = ref(false)
const recalcResult = ref<ApplyWeightsData | null>(null)

const DIMENSIONS = [
  { key: 'pitch', label: '音准' },
  { key: 'rhythm', label: '节奏' },
  { key: 'breath', label: '气息' },
  { key: 'technique', label: '发声技术' },
  { key: 'muscle', label: '肌肉力量' },
  { key: 'artistry', label: '艺术表现' },
] as const

const isCustomMode = computed(() => store.selectedPreset === 'custom')

const delta = computed(() => {
  if (!recalcResult.value || props.originalTotal === undefined) return null
  return recalcResult.value.total_score - props.originalTotal
})

// 首次进入加载预设
watch(
  () => store.isLoaded,
  (loaded) => {
    if (!loaded) store.fetchPresets()
  },
  { immediate: true },
)

function onPresetChange(): void {
  recalcResult.value = null
}

function onSliderInput(): void {
  recalcResult.value = null
}

async function onRecalc(): Promise<void> {
  if (!store.isValid) return
  recalcLoading.value = true
  try {
    recalcResult.value = await store.recalc(props.dimensionScores, props.timbreAdjustment ?? 0)
  } finally {
    recalcLoading.value = false
  }
}

defineExpose({ recalcResult })
</script>

<style scoped>
.scoring-weights-panel {
  margin-bottom: 16px;
  border-radius: 12px;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.panel-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
}
.panel-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.preset-row :deep(.el-radio-button__inner) {
  font-size: 12px;
  padding: 6px 10px;
}
.sliders {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.slider-row {
  display: grid;
  grid-template-columns: 84px 1fr 40px;
  align-items: center;
  gap: 10px;
}
.slider-label {
  font-size: 12px;
  color: var(--el-text-color-regular);
}
.slider-value {
  font-size: 12px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
.slider-sum {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  margin-top: 6px;
}
.sum-hint {
  color: var(--el-color-success);
}
.sum-hint.invalid {
  color: var(--el-color-danger);
}
.normalize-btn {
  margin-left: auto;
}
.recalc-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.recalc-total {
  font-size: 18px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.recalc-meta {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.recalc-delta {
  font-size: 12px;
}
.recalc-delta.up {
  color: var(--el-color-success);
}
.recalc-delta.down {
  color: var(--el-color-danger);
}
.panel-error {
  font-size: 12px;
  color: var(--el-color-danger);
  margin: 0;
}
</style>
