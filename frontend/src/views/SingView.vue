<script setup lang="ts">
// Phase 4 实现: Canvas 实时音高 + AudioWorklet + WebSocket
// ⚠️ onBeforeUnmount 6 步清理法 (防内存泄露)
</script>

<template>
  <div class="sing-view">
    <el-container>
      <el-main>
        <el-result icon="info" title="实时演唱" sub-title="Phase 4 实现 — Canvas + AudioWorklet + WebSocket">
          <template #extra>
            <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
          </template>
        </el-result>
      </el-main>
    </el-container>
  </div>
</template>

<style scoped>
.sing-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
