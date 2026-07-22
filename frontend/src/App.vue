<script setup lang="ts">
import { ref, onMounted } from 'vue'
import AppLayout from '@/components/layout/AppLayout.vue'
import BottomNav from '@/components/layout/BottomNav.vue'

// ---- Electron backend lifecycle ----
const backendReady = ref(!window.electronAPI) // In browser/dev, assume ready immediately
const backendStatus = ref<string>('')

onMounted(() => {
  if (window.electronAPI) {
    // Listen for backend URL assignment
    window.electronAPI.onBackendUrl((url: string) => {
      window.BACKEND_URL = url
      backendReady.value = true
      backendStatus.value = ''
    })

    // Listen for backend status changes
    window.electronAPI.onBackendStatus((status: string) => {
      backendStatus.value = status
      if (status === 'restarting') {
        backendReady.value = false
      } else if (status === 'stopped') {
        backendReady.value = false
      }
    })

    // Check if URL is already set (backend started before Vue mounted)
    window.electronAPI.getBackendUrl().then((url: string) => {
      if (url) {
        window.BACKEND_URL = url
        backendReady.value = true
      }
    })
  }
})
</script>

<template>
  <!-- Backend not ready overlay (Electron only) -->
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="!backendReady" class="backend-loading-overlay">
        <div class="backend-loading-content">
          <div class="backend-loading-spinner" />
          <h2>引擎启动中...</h2>
          <p>{{ backendStatus === 'restarting' ? '正在重连后端服务' : '正在初始化声乐评估引擎' }}</p>
          <p class="backend-loading-hint">首次启动可能需要 5-10 秒</p>
        </div>
      </div>
    </Transition>
  </Teleport>

  <AppLayout />
  <BottomNav />
</template>

<style>
/* ---- Backend Loading Overlay ---- */
.backend-loading-overlay {
  position: fixed;
  inset: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--el-bg-color, #f5f7fa);
}

.backend-loading-content {
  text-align: center;
}

.backend-loading-content h2 {
  margin-top: 24px;
  font-size: 20px;
  color: var(--el-text-color-primary);
}

.backend-loading-content p {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

.backend-loading-hint {
  opacity: 0.6;
  font-size: 12px !important;
}

.backend-loading-spinner {
  width: 48px;
  height: 48px;
  margin: 0 auto;
  border: 4px solid var(--el-border-color);
  border-top-color: var(--el-color-primary, #6366f1);
  border-radius: 50%;
  animation: backend-spin 0.8s linear infinite;
}

@keyframes backend-spin {
  to { transform: rotate(360deg); }
}

/* ---- Shared Transitions ---- */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
