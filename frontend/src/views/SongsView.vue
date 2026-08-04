<script setup lang="ts">
/**
 * SongsView — 标准歌曲库页
 *
 * 功能: 卡片网格浏览 + 搜索/风格/难度筛选 + 上传 + 删除 + 音频试听
 * v7.10: 对齐 song-library.feature BDD 契约 (选择器: #page-songs / .song-card / #songSearch /
 *        #songStats / #songsEmpty / #importFirstSongBtn / #clearSearchBtn / #pageIndicator)
 */

import { ref, reactive, computed, watch, nextTick, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Delete, VideoPlay } from '@element-plus/icons-vue'
import { useGsap } from '@/composables/useGsap'
import { useApi } from '@/composables/useApi'
import { useSongsStore } from '@/stores/songs.store'
import { ApiError } from '@/api/client'
import AudioPlayer from '@/components/AudioPlayer.vue'
import FileUploader from '@/components/FileUploader.vue'
import type { Difficulty, SongRecord, SongStyle } from '@/types/api'

const store = useSongsStore()
const { getAudioUrl } = useApi()

// ---- GSAP 入场动画 ----
const songsContainer = ref<HTMLElement | null>(null)
const { enterFrom, staggerIn } = useGsap(songsContainer)

// 卡片首次加载才做 stagger (避免每次筛选/翻页重新动画)
let didAnimateCards = false
watch(
  () => store.songs,
  (list) => {
    if (list.length > 0 && !didAnimateCards) {
      didAnimateCards = true
      nextTick(() => staggerIn('.song-card', { stagger: 0.06 }))
    }
  },
)

onMounted(() => {
  enterFrom('.page-header', { y: -8, duration: 0.35 })
  enterFrom('.songs-toolbar', { y: 12, duration: 0.4, delay: 0.1 })
  store.fetchSongs()
})

// ---- 展开详情 ----
const expandedId = ref<string | null>(null)

function toggleExpand(id: string): void {
  expandedId.value = expandedId.value === id ? null : id
}

// ---- 搜索 ----
const searchInput = ref('')

function onSearch(): void {
  store.setSearch(searchInput.value)
}

function clearSearch(): void {
  searchInput.value = ''
  onSearch()
}

// ---- 难度/风格筛选 ----
const difficultyOptions = [
  { label: '全部', value: '' as const },
  { label: '初级', value: 'beginner' as const },
  { label: '中级', value: 'intermediate' as const },
  { label: '高级', value: 'advanced' as const },
]

const styleOptions = [
  { label: '全部风格', value: '' as const },
  { label: '流行', value: 'pop' as const },
  { label: '美声', value: 'classical' as const },
  { label: '民谣', value: 'folk' as const },
  { label: '说唱', value: 'rap' as const },
]

function onStyleChange(val: string | number | undefined): void {
  store.setStyleFilter(typeof val === 'string' ? val : '')
}

// ---- 展示映射 ----
function getDifficultyLabel(d: Difficulty): string {
  return { beginner: '初级', intermediate: '中级', advanced: '高级' }[d] || d
}

function getStyleLabel(s: SongStyle): string {
  return { pop: '流行', classical: '美声', folk: '民谣', rap: '说唱' }[s] || s
}

function getDifficultyType(d: Difficulty): 'success' | 'warning' | 'danger' | 'info' {
  const map: Record<Difficulty, 'success' | 'warning' | 'danger' | 'info'> = {
    beginner: 'success',
    intermediate: 'warning',
    advanced: 'danger',
  }
  return map[d]
}

function getStyleType(s: SongStyle): '' | 'primary' | 'success' | 'warning' | 'info' {
  const map: Record<SongStyle, '' | 'primary' | 'success' | 'warning' | 'info'> = {
    pop: '',
    classical: 'primary',
    folk: 'success',
    rap: 'warning',
  }
  return map[s]
}

function formatDuration(seconds: number): string {
  if (!isFinite(seconds) || seconds <= 0) return '--:--'
  const m = Math.floor(seconds / 60)
  const s = Math.floor(seconds % 60)
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
}

function formatDate(iso: string): string {
  if (!iso) return '—'
  return iso.replace('T', ' ').slice(0, 16)
}

// ---- 搜索关键词高亮 (安全: 拆分渲染, 不用 v-html; 每段带唯一 key) ----
interface HighlightPart {
  key: string
  text: string
  hit: boolean
}

function highlightTitle(title: string): HighlightPart[] {
  const q = store.searchQuery.trim()
  if (!q) return [{ key: 'full', text: title, hit: false }]
  const lower = title.toLowerCase()
  const ql = q.toLowerCase()
  const parts: HighlightPart[] = []
  let idx = 0
  let n = 0
  while (idx < title.length) {
    const found = lower.indexOf(ql, idx)
    if (found === -1) {
      parts.push({ key: `p${n++}`, text: title.slice(idx), hit: false })
      break
    }
    if (found > idx) parts.push({ key: `p${n++}`, text: title.slice(idx, found), hit: false })
    parts.push({ key: `p${n++}`, text: title.slice(found, found + q.length), hit: true })
    idx = found + q.length
  }
  return parts.length ? parts : [{ key: 'full', text: title, hit: false }]
}

// ---- 删除 ----
async function handleDelete(song: SongRecord): Promise<void> {
  try {
    await ElMessageBox.confirm(
      `确定删除「${song.metadata.title} - ${song.metadata.artist}」？`,
      '确认删除',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
  } catch {
    return // 用户取消
  }
  try {
    await store.deleteSong(song.id)
    ElMessage.success('已删除')
    if (expandedId.value === song.id) expandedId.value = null
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '删除失败')
  }
}

// ---- 上传对话框 ----
const form = reactive({
  title: '',
  artist: '',
  key: 'C',
  bpm: 0,
  difficulty: 'beginner' as Difficulty,
  style: 'pop' as SongStyle,
  file: null as File | null,
  fileName: '',
})

function onFileSelected(file: File): void {
  form.file = file
  form.fileName = file.name
}

function onFileError(message: string): void {
  ElMessage.warning(message)
}

function cancelUpload(): void {
  store.closeUploadDialog()
  form.title = ''
  form.artist = ''
  form.key = 'C'
  form.bpm = 0
  form.difficulty = 'beginner'
  form.style = 'pop'
  form.file = null
  form.fileName = ''
}

async function submitUpload(): Promise<void> {
  if (!form.title.trim() || !form.artist.trim()) {
    ElMessage.warning('歌名和歌手不能为空')
    return
  }
  try {
    const fd = new FormData()
    fd.append('title', form.title.trim())
    fd.append('artist', form.artist.trim())
    fd.append('key', form.key.trim() || 'C')
    fd.append('bpm', String(form.bpm))
    fd.append('difficulty', form.difficulty)
    fd.append('style', form.style)
    if (form.file) fd.append('file', form.file, form.fileName || form.file.name)
    await store.createSong(fd)
    ElMessage.success('歌曲已添加')
    cancelUpload()
  } catch (e) {
    ElMessage.error(e instanceof ApiError ? e.message : '添加失败')
  }
}

// 判断是"曲库为空"还是"搜索无结果"
const isEmptyLibrary = computed(
  () =>
    !store.loading &&
    !store.hasSongs &&
    !store.searchQuery &&
    !store.styleFilter &&
    !store.difficultyFilter,
)
</script>

<template>
  <div ref="songsContainer" id="page-songs" class="songs-view">
    <!-- 页面标题 -->
    <div class="page-header">
      <h2 class="page-title">曲库</h2>
      <el-button
        type="primary"
        class="btn-import-song"
        :icon="Plus"
        @click="store.openUploadDialog()"
      >
        导入歌曲
      </el-button>
    </div>

    <!-- 工具栏: 搜索 + 难度筛选 + 风格筛选 + 统计 -->
    <div class="songs-toolbar">
      <div class="toolbar-left">
        <el-input
          id="songSearch"
          v-model="searchInput"
          placeholder="搜索歌名或歌手..."
          clearable
          :prefix-icon="Search"
          class="search-input"
          @input="onSearch"
          @clear="onSearch"
        />

        <div class="filter-group" role="group" aria-label="难度筛选">
          <button
            v-for="opt in difficultyOptions"
            :key="opt.value"
            class="filter-btn"
            :class="{ active: store.difficultyFilter === opt.value }"
            :data-filter="opt.label"
            @click="store.setDifficultyFilter(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>

        <el-select
          id="styleFilter"
          :model-value="store.styleFilter"
          placeholder="全部风格"
          clearable
          class="style-select"
          @change="onStyleChange"
        >
          <el-option
            v-for="opt in styleOptions"
            :key="opt.value"
            :label="opt.label"
            :value="opt.value"
          />
        </el-select>
      </div>

      <div class="toolbar-right">
        <span id="songStats" class="song-stats">共 {{ store.total }} 首歌曲</span>
        <el-button
          v-if="store.searchQuery"
          id="clearSearchBtn"
          size="small"
          text
          type="primary"
          @click="clearSearch"
        >
          清空搜索
        </el-button>
      </div>
    </div>

    <!-- 错误提示 -->
    <el-alert
      v-if="store.error"
      :title="store.error"
      type="error"
      show-icon
      closable
      class="error-alert"
      @close="store.error = null"
    />

    <!-- 加载态: v-loading 于网格容器 (避免 skeleton, 对齐 BDD) -->
    <div v-loading="store.loading" class="songs-grid" element-loading-text="加载中...">
      <!-- 歌曲卡片网格 -->
      <div
        v-for="song in store.songs"
        :key="song.id"
        class="song-card"
        :class="{ expanded: expandedId === song.id }"
        @click="toggleExpand(song.id)"
      >
        <div class="song-card-main">
          <div class="song-card-play" :class="{ ready: !!song.filepath }">
            <el-icon :size="20"><VideoPlay /></el-icon>
          </div>

          <div class="song-card-info">
            <div class="song-title">
              <span
                v-for="part in highlightTitle(song.metadata.title)"
                :key="part.key"
                :class="{ 'search-highlight': part.hit }"
              >{{ part.text }}</span>
            </div>
            <div class="song-artist">{{ song.metadata.artist }}</div>
          </div>

          <div class="song-tags">
            <el-tag :type="getDifficultyType(song.metadata.difficulty)" size="small">
              {{ getDifficultyLabel(song.metadata.difficulty) }}
            </el-tag>
            <el-tag :type="getStyleType(song.metadata.style)" size="small" effect="plain">
              {{ getStyleLabel(song.metadata.style) }}
            </el-tag>
          </div>

          <div class="song-duration">{{ formatDuration(song.duration_seconds) }}</div>
        </div>

        <!-- 展开详情 (点击卡片) -->
        <div v-if="expandedId === song.id" class="song-detail">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="调性">{{ song.metadata.key || '—' }}</el-descriptions-item>
            <el-descriptions-item label="BPM">{{ song.metadata.bpm || '—' }}</el-descriptions-item>
            <el-descriptions-item label="难度">{{ getDifficultyLabel(song.metadata.difficulty) }}</el-descriptions-item>
            <el-descriptions-item label="风格">{{ getStyleLabel(song.metadata.style) }}</el-descriptions-item>
            <el-descriptions-item label="时长">{{ formatDuration(song.duration_seconds) }}</el-descriptions-item>
            <el-descriptions-item label="添加时间">{{ formatDate(song.created_at) }}</el-descriptions-item>
          </el-descriptions>

          <div v-if="song.filepath" class="audio-preview">
            <AudioPlayer :audio-url="getAudioUrl(song.filepath)" />
          </div>
          <p v-else class="no-audio-hint">该歌曲未上传音频，无法试听</p>

          <div class="detail-actions">
            <el-button
              type="danger"
              plain
              size="small"
              :icon="Delete"
              @click.stop="handleDelete(song)"
            >
              删除
            </el-button>
          </div>
        </div>
      </div>

      <!-- 空曲库 -->
      <div v-if="isEmptyLibrary" id="songsEmpty" class="empty-state">
        <el-empty description="曲库为空" />
        <el-button
          type="primary"
          id="importFirstSongBtn"
          :icon="Plus"
          @click="store.openUploadDialog()"
        >
          导入第一首标准歌曲
        </el-button>
      </div>

      <!-- 搜索/筛选无结果 -->
      <div v-else-if="!store.loading && !store.hasSongs" class="search-empty">
        <el-empty description="未找到匹配歌曲" />
        <el-button @click="clearSearch">清空搜索</el-button>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="store.total > store.pageSize" class="pagination-wrapper">
      <el-pagination
        :current-page="store.currentPage"
        :page-size="store.pageSize"
        :total="store.total"
        layout="prev, pager, next, total"
        background
        small
        @current-change="store.goToPage"
      />
      <span id="pageIndicator" class="page-indicator">
        第 {{ store.currentPage }} 页 / 共 {{ store.totalPages }} 页
      </span>
    </div>

    <!-- 上传歌曲对话框 -->
    <el-dialog
      v-model="store.showUploadDialog"
      title="导入歌曲"
      width="520px"
      :close-on-click-modal="false"
      append-to-body
    >
      <el-form label-width="80px">
        <el-form-item label="歌名" required>
          <el-input v-model="form.title" placeholder="歌曲名称" maxlength="100" />
        </el-form-item>
        <el-form-item label="歌手" required>
          <el-input v-model="form.artist" placeholder="歌手姓名" maxlength="100" />
        </el-form-item>
        <el-form-item label="调性">
          <el-input v-model="form.key" placeholder="如 C / D# / Fm" maxlength="10" class="key-input" />
        </el-form-item>
        <el-form-item label="BPM">
          <el-input-number v-model="form.bpm" :min="0" :max="999" />
        </el-form-item>
        <el-form-item label="难度">
          <el-select v-model="form.difficulty">
            <el-option label="初级" value="beginner" />
            <el-option label="中级" value="intermediate" />
            <el-option label="高级" value="advanced" />
          </el-select>
        </el-form-item>
        <el-form-item label="风格">
          <el-select v-model="form.style">
            <el-option label="流行" value="pop" />
            <el-option label="美声" value="classical" />
            <el-option label="民谣" value="folk" />
            <el-option label="说唱" value="rap" />
          </el-select>
        </el-form-item>
        <el-form-item label="音频文件">
          <FileUploader @file-selected="onFileSelected" @error="onFileError" />
          <p v-if="form.fileName" class="file-name">{{ form.fileName }}</p>
          <p class="form-hint">可选: 不上传音频也可以录入歌曲元数据供后续练习使用</p>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="cancelUpload">取消</el-button>
        <el-button type="primary" :loading="store.uploading" @click="submitUpload">
          确认添加
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.songs-view {
  max-width: 1200px;
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

.songs-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input {
  width: 220px;
}

/* 难度筛选按钮组 */
.filter-group {
  display: inline-flex;
  background: var(--el-fill-color-light);
  border-radius: var(--el-border-radius-base);
  padding: 2px;
}

.filter-btn {
  border: none;
  background: transparent;
  padding: 5px 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  border-radius: var(--el-border-radius-small);
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
}

.filter-btn:hover {
  color: var(--el-color-primary);
}

.filter-btn.active {
  background: var(--el-bg-color);
  color: var(--el-color-primary);
  font-weight: 600;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.style-select {
  width: 120px;
}

.song-stats {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.error-alert {
  margin-bottom: 16px;
}

/* 卡片网格 */
.songs-grid {
  min-height: 200px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.song-card {
  background: var(--el-bg-color-overlay);
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s, border-color 0.2s;
}

.song-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  border-color: var(--el-color-primary-light-5);
}

.song-card.expanded {
  border-color: var(--el-color-primary);
}

.song-card-main {
  display: flex;
  align-items: center;
  gap: 12px;
}

.song-card-play {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--el-fill-color-light);
  color: var(--el-text-color-placeholder);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s, color 0.2s;
}

.song-card-play.ready {
  color: var(--el-color-primary);
}

.song-card:hover .song-card-play.ready {
  background: var(--el-color-primary-light-9);
}

.song-card-info {
  flex: 1;
  min-width: 0;
}

.song-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.song-artist {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.search-highlight {
  color: var(--el-color-primary);
  font-weight: 700;
}

.song-tags {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex-shrink: 0;
}

.song-duration {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
  font-variant-numeric: tabular-nums;
  flex-shrink: 0;
}

/* 展开详情 */
.song-detail {
  border-top: 1px solid var(--el-border-color-lighter);
  margin-top: 14px;
  padding-top: 14px;
}

.audio-preview {
  margin-top: 12px;
}

.no-audio-hint {
  margin: 12px 0 0;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

.detail-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 12px;
}

/* 空状态 */
.empty-state,
.search-empty {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 0;
}

/* 分页 */
.pagination-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  margin-top: 24px;
  padding-bottom: 24px;
}

.page-indicator {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

/* 上传表单 */
.key-input {
  width: 120px;
}

.file-name {
  margin: 8px 0 0;
  font-size: 13px;
  color: var(--el-color-primary);
}

.form-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

/* 移动端 */
@media (max-width: 767px) {
  .songs-view {
    padding-bottom: 72px;
  }
  .songs-toolbar {
    flex-direction: column;
    align-items: flex-start;
  }
  .toolbar-left {
    width: 100%;
  }
  .search-input {
    width: 100%;
  }
  .songs-grid {
    grid-template-columns: 1fr;
  }
}
</style>
