<script setup lang="ts">
/**
 * ScoreCard — 可复用评分卡片
 *
 * 显示单个维度的：标签、分数、权重、启发式标记、子维度分数
 * 颜色根据分数自动变化 (绿→蓝→黄→橙→红)
 */

import { computed } from 'vue'

const props = defineProps<{
  label: string
  score: number
  weight: number
  isHeuristic?: boolean
  subScores?: Record<string, number>
}>()

const emit = defineEmits<{
  (e: 'click'): void
}>()

const scoreColor = computed(() => {
  if (props.score >= 88) return 'var(--el-color-success)'
  if (props.score >= 78) return '#3b82f6'
  if (props.score >= 62) return 'var(--el-color-primary)'
  if (props.score >= 45) return 'var(--el-color-warning)'
  if (props.score >= 25) return '#f97316'
  return 'var(--el-color-danger)'
})

const levelLabel = computed(() => {
  if (props.score >= 88) return '专业级'
  if (props.score >= 78) return '优秀'
  if (props.score >= 62) return '良好'
  if (props.score >= 45) return '中等'
  if (props.score >= 25) return '及格'
  return '待改进'
})

const subScoreEntries = computed(() => {
  if (!props.subScores) return []
  return Object.entries(props.subScores).map(([key, val]) => ({
    key: formatSubScoreKey(key),
    val: Math.round(val),
  }))
})

function formatSubScoreKey(key: string): string {
  const map: Record<string, string> = {
    articulation_clarity: '咬字清晰度',
    breath_voice_ratio: '气声比',
    body_muscle_strength: '身体肌肉',
    facial_muscle_strength: '面部肌肉',
    long_note_support: '长音支撑',
    dynamic_control: '动态控制',
    breath_design: '气口设计',
    breath_technique: '气声技巧',
    vibrato_quality: '颤音品质',
    phrase_expression: '乐句表现',
    pitch_variation: '音高变化',
  }
  return map[key] || key
}
</script>

<template>
  <div class="score-card" :class="{ heuristic: isHeuristic }" @click="emit('click')">
    <div class="score-header">
      <div class="score-label-group">
        <span class="score-label">{{ label }}</span>
        <span class="score-weight">权重 {{ weight }}%</span>
        <el-tag v-if="isHeuristic" size="small" type="warning" effect="plain">
          估算值
        </el-tag>
      </div>
      <el-tag
        :color="scoreColor"
        size="small"
        class="score-level-tag"
        effect="dark"
      >
        {{ levelLabel }}
      </el-tag>
    </div>

    <div class="score-body">
      <span class="score-value" :style="{ color: scoreColor }">
        {{ Math.round(score) }}
      </span>
      <span class="score-unit">分</span>
    </div>

    <el-progress
      :percentage="score"
      :color="scoreColor"
      :stroke-width="6"
      :show-text="false"
      class="score-bar"
    />

    <!-- 子维度 -->
    <div v-if="subScoreEntries.length > 0" class="sub-scores">
      <div v-for="sub in subScoreEntries" :key="sub.key" class="sub-score-row">
        <span class="sub-label">{{ sub.key }}</span>
        <el-progress
          :percentage="sub.val"
          :stroke-width="4"
          :show-text="false"
          class="sub-bar"
        />
        <span class="sub-value">{{ sub.val }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.score-card {
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: var(--el-border-radius-base);
  padding: 16px;
  cursor: default;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.score-card:hover {
  border-color: var(--el-color-primary-light-5);
}

.score-card.heuristic {
  border-left: 3px solid var(--el-color-warning);
}

.score-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.score-label-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.score-label {
  font-weight: 600;
  font-size: 15px;
  color: var(--el-text-color-primary);
}

.score-weight {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.score-body {
  display: flex;
  align-items: baseline;
  gap: 4px;
  margin-bottom: 8px;
}

.score-value {
  font-size: 36px;
  font-weight: 700;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.score-unit {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.score-bar {
  margin-bottom: 4px;
}

.sub-scores {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.sub-score-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.sub-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  min-width: 72px;
  flex-shrink: 0;
}

.sub-bar {
  flex: 1;
}

.sub-value {
  font-size: 12px;
  color: var(--el-text-color-regular);
  min-width: 24px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}
</style>
