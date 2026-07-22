<script setup lang="ts">
/**
 * ScoreRadar — 六维雷达图组件
 *
 * 基于 Chart.js radar chart，展示六维评分
 * 维度: 音准(10%) / 节奏(10%) / 气息(20%) / 发声技术(25%) / 肌肉力量(25%) / 艺术表现(10%)
 */

import { computed, ref, watch } from 'vue'
import { Radar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  RadialLinearScale,
  PointElement,
  LineElement,
  Filler,
  Tooltip,
  Legend,
} from 'chart.js'
import type { SixDimensionScores } from '@/types/score'
import type { TooltipItem } from 'chart.js'

ChartJS.register(RadialLinearScale, PointElement, LineElement, Filler, Tooltip, Legend)

const props = defineProps<{
  scores: SixDimensionScores
  heuristicDimensions?: string[]
}>()

const chartRef = ref<any>(null)

const labels = ['音准', '节奏', '气息', '发声技术', '肌肉力量', '艺术表现']

const chartData = computed(() => ({
  labels,
  datasets: [
    {
      label: '你的评分',
      data: [
        props.scores.pitch,
        props.scores.rhythm,
        props.scores.breath,
        props.scores.technique,
        props.scores.muscle_strength,
        props.scores.artistry,
      ],
      backgroundColor: 'rgba(99, 102, 241, 0.15)',
      borderColor: 'rgba(99, 102, 241, 0.8)',
      borderWidth: 2,
      pointBackgroundColor: 'rgba(99, 102, 241, 1)',
      pointBorderColor: '#fff',
      pointBorderWidth: 2,
      pointRadius: 4,
      pointHoverRadius: 6,
    },
    {
      label: '基准线 (60分)',
      data: [60, 60, 60, 60, 60, 60],
      backgroundColor: 'transparent',
      borderColor: 'rgba(148, 163, 184, 0.3)',
      borderWidth: 1,
      borderDash: [4, 4],
      pointRadius: 0,
      pointHoverRadius: 0,
    },
  ],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: true,
  scales: {
    r: {
      beginAtZero: true,
      max: 100,
      min: 0,
      ticks: {
        stepSize: 20,
        backdropColor: 'transparent',
        font: { size: 10 },
      },
      pointLabels: {
        font: { size: 13, weight: 'bold' as const },
        color: '#64748b',
      },
      grid: {
        color: 'rgba(148, 163, 184, 0.15)',
      },
      angleLines: {
        color: 'rgba(148, 163, 184, 0.15)',
      },
    },
  },
  plugins: {
    legend: {
      display: true,
      position: 'bottom' as const,
      labels: {
        filter: (item: { text: string }) => item.text !== '基准线 (60分)',
        usePointStyle: true,
        padding: 20,
        font: { size: 12 },
      },
    },
    tooltip: {
      callbacks: {
        label: (ctx: TooltipItem<'radar'>) => {
          if (ctx.datasetIndex === 1) return ''
          return `${labels[ctx.dataIndex]}: ${Math.round(ctx.raw as number)} 分`
        },
      },
    },
  },
}

watch(
  () => props.scores,
  () => {
    chartRef.value?.chart?.update()
  },
  { deep: true },
)
</script>

<template>
  <div class="score-radar">
    <Radar ref="chartRef" :data="chartData" :options="chartOptions as any" />
  </div>
</template>

<style scoped>
.score-radar {
  max-width: 420px;
  margin: 0 auto;
  padding: 16px;
}
</style>
