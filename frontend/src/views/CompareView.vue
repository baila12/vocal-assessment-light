<script setup lang="ts">
// Phase 4 实现: 双文件上传 + DTW 结果可视化
</script>

<template>
  <div class="compare-view">
    <el-container>
      <el-main>
        <el-result icon="info" title="对比分析" sub-title="Phase 4 实现 — DTW 双文件对比">
          <template #extra>
            <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
          </template>
        </el-result>
      </el-main>
    </el-container>
  </div>
</template>

<style scoped>
.compare-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
