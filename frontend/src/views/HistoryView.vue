<script setup lang="ts">
/**
 * HistoryView — 历史记录页
 *
 * 功能: ElTable 分页列表 + 日期筛选 + 批量删除 + 搜索
 * v7.0: UTF-8 重写，修复 v6.3 GBK 乱码问题
 */

import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Delete } from '@element-plus/icons-vue'
import { useHistoryStore } from '@/stores/history.store'
import type { HistoryRecord } from '@/types/api'

const router = useRouter()
const store = useHistoryStore()

const searchInput = ref('')

// ---- 表格列配置 ----
const columns = [
  { prop: 'id', label: '#', width: 60, align: 'center' as const },
  { prop: 'filename', label: '文件名', minWidth: 180 },
  { prop: 'mode', label: '模式', width: 80, align: 'center' as const },
  { prop: 'total_score', label: '总分', width: 80, align: 'center' as const },
  { prop: 'level', label: '等级', width: 80, align: 'center' as const },
  { prop: 'created_at', label: '日期', width: 160 },
  { prop: 'actions', label: '操作', width: 120, align: 'center' as const },
]

// ---- 日期筛选选项 ----
const filterOptions = [
  { label: '全部', value: 'all' as const },
  { label: '今天', value: 'today' as const },
  { label: '本周', value: 'week' as const },
  { label: '本月', value: 'month' as const },
]

// ---- 等级标签类型映射 ----
function getLevelType(level: string): 'success' | 'primary' | 'warning' | 'danger' | 'info' | '' {
  const map: Record<string, 'success' | 'primary' | 'warning' | 'danger' | 'info' | ''> = {
    '专业级': 'success',
    'S': 'success',
    '优秀': 'primary',
    'A': 'primary',
    '良好': 'success',
    'B': 'success',
    '中等': 'warning',
    'C': 'warning',
    '及格': 'danger',
    'D': 'danger',
    '待改进': 'danger',
    'E': 'danger',
  }
  return map[level] || 'info'
}

// ---- 模式标签 ----
function getModeLabel(mode: string): string {
  return mode === 'professional' ? '专业' : '快速'
}

// ---- 选择处理 ----
function handleSelectionChange(rows: HistoryRecord[]): void {
  // 通过 store 方法批量设置选中状态，避免直接修改 store 内部状态
  store.setSelectedIds(rows.map((r) => r.id))
}

// ---- 操作 ----
function viewReport(row: HistoryRecord): void {
  router.push(`/report/${row.id}`)
}

async function deleteOne(row: HistoryRecord): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除「${row.filename}」的分析记录？`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await store.deleteRecord(row.id)
    ElMessage.success('已删除')
  } catch {
    // 用户取消
  }
}

async function deleteSelected(): Promise<void> {
  if (store.selectedIds.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确定删除选中的 ${store.selectedIds.length} 条记录？`,
      '批量删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await store.deleteBatch()
    ElMessage.success('批量删除完成')
  } catch {
    // 用户取消
  }
}

async function clearAll(): Promise<void> {
  if (store.records.length === 0) return
  try {
    await ElMessageBox.confirm(
      '确定清空所有历史记录？此操作不可恢复。',
      '清空全部',
      { type: 'error', confirmButtonText: '确认清空', cancelButtonText: '取消' },
    )
    await store.deleteAll()
    ElMessage.success('已清空全部记录')
  } catch {
    // 用户取消
  }
}

// ---- 搜索 ----
function onSearch(): void {
  store.setSearch(searchInput.value)
}

// ---- 初始化 ----
onMounted(() => {
  store.fetchHistory()
})
</script>

<template>
  <div class="history-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title">历史记录</h2>
      <div class="header-actions">
        <el-button
          type="danger"
          plain
          size="small"
          :disabled="store.records.length === 0"
          @click="clearAll"
        >
          清空全部
        </el-button>
      </div>
    </div>

    <!-- 工具栏: 筛选 + 搜索 + 批量操作 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <el-radio-group
          :model-value="store.filter"
          size="small"
          @change="(val: string) => store.setFilter(val as any)"
        >
          <el-radio-button
            v-for="opt in filterOptions"
            :key="opt.value"
            :value="opt.value"
            :label="opt.label"
          />
        </el-radio-group>
      </div>
      <div class="toolbar-right">
        <el-input
          v-model="searchInput"
          placeholder="搜索文件名..."
          size="small"
          clearable
          :prefix-icon="Search"
          class="search-input"
          @input="onSearch"
          @clear="onSearch"
        />
        <el-button
          v-if="store.hasSelection"
          type="danger"
          size="small"
          :icon="Delete"
          @click="deleteSelected"
        >
          删除选中 ({{ store.selectedIds.length }})
        </el-button>
      </div>
    </div>

    <!-- 表格 -->
    <el-table
      :data="store.paginatedRecords"
      v-loading="store.loading"
      :element-loading-text="'加载中...'"
      @selection-change="handleSelectionChange"
      stripe
      class="history-table"
      empty-text="暂无分析记录"
    >
      <el-table-column type="selection" width="44" />

      <el-table-column
        v-for="col in columns"
        :key="col.prop"
        :prop="col.prop"
        :label="col.label"
        :width="col.width"
        :min-width="col.minWidth"
        :align="col.align"
      >
        <template v-if="col.prop === 'level'" #default="{ row }">
          <el-tag :type="getLevelType(row.level)" size="small">
            {{ row.level }} ({{ row.grade }})
          </el-tag>
        </template>

        <template v-else-if="col.prop === 'mode'" #default="{ row }">
          <el-tag :type="row.mode === 'professional' ? 'primary' : 'info'" size="small">
            {{ getModeLabel(row.mode) }}
          </el-tag>
        </template>

        <template v-else-if="col.prop === 'total_score'" #default="{ row }">
          <span class="score-cell">{{ Math.round(row.total_score) }}</span>
        </template>

        <template v-else-if="col.prop === 'actions'" #default="{ row }">
          <div class="action-btns">
            <el-button text size="small" type="primary" @click="viewReport(row)">
              查看
            </el-button>
            <el-button text size="small" type="danger" @click="deleteOne(row)">
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div class="pagination-wrapper">
      <el-pagination
        v-model:current-page="store.currentPage"
        :page-size="store.pageSize"
        :total="store.filteredRecords.length"
        layout="prev, pager, next, total"
        background
        small
        @current-change="store.goToPage"
      />
    </div>
  </div>
</template>

<style scoped>
.history-view {
  max-width: 960px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  margin: 0;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-right {
  display: flex;
  gap: 8px;
  align-items: center;
}

.search-input {
  width: 200px;
}

.history-table {
  width: 100%;
  border-radius: var(--el-border-radius-base);
}

.score-cell {
  font-weight: 700;
  font-size: 15px;
  color: var(--el-color-primary);
  font-variant-numeric: tabular-nums;
}

.action-btns {
  display: flex;
  gap: 2px;
  justify-content: center;
}

.pagination-wrapper {
  display: flex;
  justify-content: center;
  margin-top: 20px;
  padding-bottom: 24px;
}

@media (max-width: 767px) {
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
  }
  .toolbar-right {
    width: 100%;
  }
  .search-input {
    flex: 1;
  }
  .history-view {
    padding-bottom: 72px;
  }
}
</style>
