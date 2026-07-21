<script setup lang="ts">
// Phase 4 实现: 六维雷达图 + 音高曲线 + 音频播放器
</script>

<template>
  <div class="report-view">
    <el-container>
      <el-main>
        <el-result icon="info" title="报告页面" sub-title="Phase 4 实现 — 六维雷达图 + 启发式标签">
          <template #extra>
            <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
          </template>
        </el-result>
      </el-main>
    </el-container>
  </div>
</template>

<style scoped>
.report-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
