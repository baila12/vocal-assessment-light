/**
 * useMediaRecorder — 录音控制 composable
 *
 * 管理：MediaRecorder 生命周期、录音状态、音频 Blob 输出
 * 与 useAudioContext 配合使用 — 本 composable 管理录音，useAudioContext 管理实时音频处理
 */

import { ref, onBeforeUnmount } from 'vue'

export interface RecordingOptions {
  mimeType?: string
  audioBitsPerSecond?: number
}

export function useMediaRecorder() {
  const isRecording = ref(false)
  const isPaused = ref(false)
  const duration = ref(0)
  const error = ref<string | null>(null)

  let mediaRecorder: MediaRecorder | null = null
  let mediaStream: MediaStream | null = null
  let chunks: Blob[] = []
  let durationTimer: ReturnType<typeof setInterval> | null = null

  const DEFAULT_OPTIONS: RecordingOptions = {
    mimeType: 'audio/webm;codecs=opus',
    audioBitsPerSecond: 128000,
  }

  function getSupportedMimeType(): string {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/mp4',
    ]
    for (const t of types) {
      if (MediaRecorder.isTypeSupported(t)) return t
    }
    return 'audio/webm' // fallback
  }

  async function start(
    onDataAvailable?: (blob: Blob) => void,
    options: RecordingOptions = {},
  ): Promise<void> {
    error.value = null
    chunks = []

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })

      const opts = { ...DEFAULT_OPTIONS, ...options }
      opts.mimeType = getSupportedMimeType()

      mediaRecorder = new MediaRecorder(mediaStream, {
        mimeType: opts.mimeType,
        audioBitsPerSecond: opts.audioBitsPerSecond,
      })

      mediaRecorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          chunks.push(event.data)
          onDataAvailable?.(event.data)
        }
      }

      mediaRecorder.onerror = () => {
        error.value = '录音出错'
        stop()
      }

      mediaRecorder.start(1000) // 每秒收集 chunk
      isRecording.value = true
      isPaused.value = false
      duration.value = 0

      // 计时器
      durationTimer = setInterval(() => {
        duration.value++
      }, 1000)
    } catch (e) {
      const msg =
        e instanceof DOMException && e.name === 'NotAllowedError'
          ? '麦克风权限被拒绝'
          : `录音启动失败: ${e}`
      error.value = msg
      throw new Error(msg)
    }
  }

  function pause(): void {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
      mediaRecorder.pause()
      isPaused.value = true
      if (durationTimer) clearInterval(durationTimer)
    }
  }

  function resume(): void {
    if (mediaRecorder && mediaRecorder.state === 'paused') {
      mediaRecorder.resume()
      isPaused.value = false
      durationTimer = setInterval(() => {
        duration.value++
      }, 1000)
    }
  }

  function stop(): Blob | null {
    if (durationTimer) {
      clearInterval(durationTimer)
      durationTimer = null
    }

    // 停止 MediaRecorder
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    }

    // 停止媒体流
    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop())
      mediaStream = null
    }

    isRecording.value = false
    isPaused.value = false

    const currentMimeType = mediaRecorder?.mimeType || 'audio/webm'
    mediaRecorder = null

    if (chunks.length === 0) return null

    return new Blob(chunks, { type: currentMimeType })
  }

  /** 获取完整录音文件的 File 对象（用于上传） */
  function getAudioFile(filename = 'recording.webm'): File | null {
    const blob = stop()
    if (!blob) return null
    return new File([blob], filename, { type: blob.type })
  }

  function formatDuration(totalSeconds: number): string {
    const mins = Math.floor(totalSeconds / 60)
    const secs = totalSeconds % 60
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
  }

  onBeforeUnmount(() => {
    if (durationTimer) clearInterval(durationTimer)
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop()
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop())
    }
  })

  return {
    isRecording,
    isPaused,
    duration,
    error,
    start,
    pause,
    resume,
    stop,
    getAudioFile,
    formatDuration,
  }
}
