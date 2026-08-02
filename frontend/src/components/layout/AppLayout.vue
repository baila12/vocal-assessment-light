<script setup lang="ts">
import TopNav from './TopNav.vue'
</script>

<template>
  <el-container class="app-layout">
    <el-header class="app-header" height="56px">
      <TopNav />
    </el-header>
    <el-main class="app-main">
      <router-view v-slot="{ Component, route }">
        <transition name="page" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </el-main>
  </el-container>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
  background-color: var(--el-bg-color);
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 1000;
  padding: 0;
  background-color: var(--el-bg-color-overlay);
  border-bottom: 1px solid var(--el-border-color-lighter);
  backdrop-filter: blur(8px);
}

.app-main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px;
  min-height: calc(100vh - 56px);
}

/* ---- 页面过渡动画 ---- */
.page-enter-active,
.page-leave-active {
  transition: opacity 0.3s ease, transform 0.3s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(12px);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}
</style>
