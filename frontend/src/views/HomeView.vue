<script setup lang="ts">
import { ref } from 'vue'

const backendStatus = ref<string>('检查中...')

async function checkHealth() {
  try {
    const resp = await fetch('http://127.0.0.1:8000/health')
    const data = await resp.json()
    backendStatus.value = `${data.status} (v${data.version})`
  } catch {
    backendStatus.value = '后端未启动'
  }
}

checkHealth()
</script>

<template>
  <div class="home-view">
    <el-container>
      <el-main>
        <div class="hero">
          <el-icon :size="48" color="var(--el-color-primary)">
            <Headset />
          </el-icon>
          <h1>VAS v7.0 — 声乐评估系统</h1>
          <p class="subtitle">上传你的演唱录音，获取专业级多维度评分</p>
          <el-tag :type="backendStatus.includes('healthy') ? 'success' : 'danger'" size="large">
            {{ backendStatus }}
          </el-tag>
        </div>

        <el-divider />

        <el-row :gutter="16" justify="center">
          <el-col :xs="24" :sm="8" v-for="mode in modes" :key="mode.key">
            <el-card shadow="hover" class="mode-card">
              <template #header>
                <div class="card-header">
                  <el-icon :size="24"><component :is="mode.icon" /></el-icon>
                  <span>{{ mode.title }}</span>
                </div>
              </template>
              <p>{{ mode.desc }}</p>
              <template #footer>
                <el-button type="primary" disabled>即将上线</el-button>
              </template>
            </el-card>
          </el-col>
        </el-row>
      </el-main>
    </el-container>
  </div>
</template>

<script lang="ts">
const modes = [
  { key: 'quick', title: '快速评估', desc: '15-60 秒快速打分', icon: 'Lightning' },
  { key: 'professional', title: '专业评估', desc: 'Demucs 人声分离 + 深度分析', icon: 'Aim' },
  { key: 'compare', title: '对比分析', desc: 'DTW 双文件对比', icon: 'DataAnalysis' },
]
</script>

<style scoped>
.home-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hero {
  text-align: center;
  padding: 40px 0;
}
.hero h1 {
  margin: 16px 0 8px;
  font-size: 28px;
}
.subtitle {
  color: var(--el-text-color-secondary);
  margin-bottom: 16px;
}
.mode-card {
  text-align: center;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
</style>
