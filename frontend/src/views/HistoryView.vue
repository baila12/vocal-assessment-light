<script setup lang="ts">
// Phase 4 实现: ElTable + ElPagination + UTF-8 重写
</script>

<template>
  <div class="history-view">
    <el-container>
      <el-main>
        <el-result icon="info" title="历史记录" sub-title="Phase 4 实现 — 表格分页 + 批量删除">
          <template #extra>
            <el-button type="primary" @click="$router.push('/')">返回首页</el-button>
          </template>
        </el-result>
      </el-main>
    </el-container>
  </div>
</template>

<style scoped>
.history-view {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
