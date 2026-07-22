<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { usePreferencesStore } from '@/stores/preferences.store'
import { Moon, Sunny } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const preferences = usePreferencesStore()

const navItems = [
  { path: '/', label: '首页', icon: 'HomeFilled' },
  { path: '/sing', label: '演唱', icon: 'Microphone' },
  { path: '/history', label: '历史', icon: 'Document' },
  { path: '/compare', label: '对比', icon: 'DataAnalysis' },
]

function navigate(path: string): void {
  router.push(path)
}
</script>

<template>
  <div class="top-nav">
    <div class="nav-brand" @click="navigate('/')">
      <el-icon :size="22" color="var(--el-color-primary)">
        <Headset />
      </el-icon>
      <span class="brand-text">VAS v7.0</span>
    </div>

    <el-menu
      :default-active="route.path"
      mode="horizontal"
      :ellipsis="false"
      class="nav-menu"
      @select="(index: string) => navigate(index)"
    >
      <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
        <el-icon><component :is="item.icon" /></el-icon>
        <span>{{ item.label }}</span>
      </el-menu-item>
    </el-menu>

    <div class="nav-actions">
      <el-switch
        :model-value="preferences.theme === 'dark'"
        inline-prompt
        :active-icon="Moon"
        :inactive-icon="Sunny"
        @change="preferences.toggleTheme()"
        aria-label="切换主题"
      />
    </div>
  </div>
</template>

<style scoped>
.top-nav {
  display: flex;
  align-items: center;
  height: 56px;
  padding: 0 16px;
  gap: 16px;
  max-width: 1200px;
  margin: 0 auto;
}

.nav-brand {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
}

.brand-text {
  font-size: 16px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  letter-spacing: -0.5px;
}

.nav-menu {
  flex: 1;
  border-bottom: none !important;
  background: transparent;
}

.nav-menu .el-menu-item {
  border-bottom: 2px solid transparent;
}

.nav-actions {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}
</style>
