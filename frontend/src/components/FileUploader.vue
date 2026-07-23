<script setup lang="ts">
/**
 * FileUploader — 拖拽上传封装组件 (v2)
 *
 * 包装 el-upload，支持拖拽 + 点击选择
 * 使用 on-change 事件 (非 before-upload) — auto-upload=false 的标准模式
 */
import { ref } from 'vue'
import type { UploadFile, UploadRawFile } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'

const props = defineProps<{
  maxSize?: number
  accept?: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'fileSelected', file: File): void
  (e: 'error', message: string): void
}>()

const ALLOWED_EXTENSIONS = ['.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac', '.webm']
const DEFAULT_MAX_SIZE = 50 * 1024 * 1024

const fileList = ref<UploadFile[]>([])
const isDragOver = ref(false)

function validateFile(rawFile: UploadRawFile): string | null {
  const ext = '.' + rawFile.name.split('.').pop()?.toLowerCase()
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    return `不支持的文件格式: ${ext}。支持: ${ALLOWED_EXTENSIONS.join(', ')}`
  }
  const maxSize = props.maxSize || DEFAULT_MAX_SIZE
  if (rawFile.size > maxSize) {
    return `文件过大，最大支持 ${(maxSize / 1024 / 1024).toFixed(0)}MB`
  }
  return null
}

function handleChange(file: UploadFile, fileListNew: UploadFile[]): void {
  // 只保留最新的一个文件
  if (fileListNew.length > 1) {
    fileList.value = [fileListNew[fileListNew.length - 1]]
  }
  const err = validateFile(file.raw as UploadRawFile)
  if (err) {
    emit('error', err)
    fileList.value = []
    return
  }
  emit('fileSelected', file.raw as File)
}

function handleRemove(): void {
  fileList.value = []
}

function handleDragOver(event: DragEvent): void {
  event.preventDefault()
  isDragOver.value = true
}
function handleDragLeave(): void {
  isDragOver.value = false
}
function handleDrop(event: DragEvent): void {
  event.preventDefault()
  isDragOver.value = false
}
</script>

<template>
  <div
    class="file-uploader"
    :class="{ 'drag-over': isDragOver, disabled }"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
  >
    <el-upload
      v-model:file-list="fileList"
      :auto-upload="false"
      :show-file-list="false"
      :accept="accept || '.wav,.mp3,.flac,.ogg,.m4a,.aac,.webm'"
      :disabled="disabled"
      :on-change="handleChange"
      :on-remove="handleRemove"
      drag
      :limit="1"
      class="upload-area"
    >
      <div class="upload-content">
        <el-icon :size="40" color="var(--el-color-primary)" class="upload-icon">
          <UploadFilled />
        </el-icon>
        <div class="upload-text">
          <p class="upload-title">拖拽音频文件到此处</p>
          <p class="upload-hint">或点击选择文件</p>
        </div>
        <p class="upload-formats">
          支持 WAV, MP3, FLAC, OGG, M4A, AAC &middot; 最大 50MB
        </p>
      </div>
    </el-upload>
  </div>
</template>

<style scoped>
.file-uploader { border-radius: var(--el-border-radius-base); transition: border-color 0.2s, background 0.2s; }
.file-uploader.drag-over { background: rgba(99, 102, 241, 0.05); }
.file-uploader.disabled { opacity: 0.5; pointer-events: none; }
.upload-area { width: 100%; }
.upload-area :deep(.el-upload) { width: 100%; }
.upload-area :deep(.el-upload-dragger) { width: 100%; padding: 32px 16px; border: 2px dashed var(--el-border-color); }
.file-uploader.drag-over :deep(.el-upload-dragger) { border-color: var(--el-color-primary); background: rgba(99, 102, 241, 0.04); }
.upload-content { display: flex; flex-direction: column; align-items: center; gap: 8px; }
.upload-icon { opacity: 0.8; }
.upload-text { text-align: center; }
.upload-title { font-size: 15px; font-weight: 600; color: var(--el-text-color-primary); margin: 0 0 4px; }
.upload-hint { font-size: 13px; color: var(--el-color-primary); margin: 0; }
.upload-formats { font-size: 11px; color: var(--el-text-color-placeholder); margin: 4px 0 0; }
</style>
