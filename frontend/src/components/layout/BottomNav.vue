<script setup lang="ts">
/**
 * BottomNav — 移动端底部导航栏
 * 仅在 viewport < 768px 时显示
 */
import { useRouter, useRoute } from 'vue-router'
import { HomeFilled, Microphone, Document, DataAnalysis } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()

const navItems = [
  { path: '/', label: '首页', icon: HomeFilled },
  { path: '/sing', label: '演唱', icon: Microphone },
  { path: '/history', label: '历史', icon: Document },
  { path: '/compare', label: '对比', icon: DataAnalysis },
]
</script>

<template>
  <nav class="bottom-nav" aria-label="移动端导航">
    <button
      v-for="item in navItems"
      :key="item.path"
      class="nav-item"
      :class="{ active: route.path === item.path || (item.path !== '/' && route.path.startsWith(item.path)) }"
      @click="router.push(item.path)"
    >
      <el-icon :size="20">
        <component :is="item.icon" />
      </el-icon>
      <span class="nav-label">{{ item.label }}</span>
    </button>
  </nav>
</template>

<style scoped>
.bottom-nav {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 56px;
  background: var(--el-bg-color-overlay);
  border-top: 1px solid var(--el-border-color-lighter);
  backdrop-filter: blur(8px);
  z-index: 1000;
  justify-content: space-around;
  align-items: center;
  padding: 0 8px;
  padding-bottom: env(safe-area-inset-bottom, 0);
}

@media (max-width: 767px) {
  .bottom-nav {
    display: flex;
  }
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px 12px;
  border: none;
  background: none;
  color: var(--el-text-color-secondary);
  cursor: pointer;
  transition: color 0.2s;
  -webkit-tap-highlight-color: transparent;
}

.nav-item.active {
  color: var(--el-color-primary);
}

.nav-label {
  font-size: 10px;
  line-height: 1;
}
</style>
