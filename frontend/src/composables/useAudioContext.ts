/**
 * useAudioContext — Web Audio API 管理 + AudioWorklet 重采样
 *
 * AudioWorklet 将浏览器原生采样率 (48kHz) 重采样到 16kHz,
 * 每 2048 samples (~128ms) 输出一个 Float32Array。
 */

import { ref, onBeforeUnmount } from 'vue'

export function useAudioContext() {
  const isRecording = ref(false)
  const audioContext = ref<AudioContext | null>(null)
  const mediaStream = ref<MediaStream | null>(null)

  let workletNode: AudioWorkletNode | null = null
  let onPcmCallback: ((pcm: Float32Array) => void) | null = null

  async function start(onPcm: (pcm: Float32Array) => void): Promise<void> {
    onPcmCallback = onPcm

    // 1. 创建 AudioContext (16kHz target)
    const ctx = new AudioContext({ sampleRate: 16000 })
    audioContext.value = ctx

    // 2. 获取麦克风权限
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: 16000,
        channelCount: 1,
        echoCancellation: true,
        noiseSuppression: true,
      },
    })
    mediaStream.value = stream

    // 3. 加载 AudioWorklet 处理器
    await ctx.audioWorklet.addModule('/audio-processor.js')

    // 4. 创建 AudioWorkletNode 并连接
    workletNode = new AudioWorkletNode(ctx, 'downsample-processor')

    workletNode.port.onmessage = (event: MessageEvent<Float32Array>) => {
      if (onPcmCallback) {
        onPcmCallback(event.data)
      }
    }

    const source = ctx.createMediaStreamSource(stream)
    source.connect(workletNode)
    workletNode.connect(ctx.destination)

    isRecording.value = true
  }

  function stop(): void {
    // 1. 停止 AudioWorklet
    if (workletNode) {
      workletNode.port.onmessage = null
      workletNode.disconnect()
      workletNode = null
    }

    // 2. 释放音频硬件锁
    if (audioContext.value && audioContext.value.state !== 'closed') {
      audioContext.value.close().catch(() => {})
      audioContext.value = null
    }

    // 3. 停止麦克风
    if (mediaStream.value) {
      mediaStream.value.getTracks().forEach((t) => t.stop())
      mediaStream.value = null
    }

    isRecording.value = false
    onPcmCallback = null
  }

  onBeforeUnmount(() => {
    stop()
  })

  return {
    isRecording,
    audioContext,
    start,
    stop,
  }
}
