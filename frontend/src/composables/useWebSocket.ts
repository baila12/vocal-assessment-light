/**
 * useWebSocket — WebSocket 连接管理 + 二进制帧发送 + 自动重连
 *
 * ADR-7: 4字节大端长度前缀协议
 * 使用方式:
 *   const { connect, send, sendPcm, close } = useWebSocket()
 */

import { ref, onBeforeUnmount } from 'vue'
import { apiClient } from '@/api/client'

export interface WsEvent {
  event: string
  [key: string]: any
}

export function useWebSocket() {
  const isConnected = ref(false)
  const isLoading = ref(false)
  const lastEvent = ref<WsEvent | null>(null)
  const error = ref<string | null>(null)

  let ws: WebSocket | null = null
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let reconnectAttempts = 0
  const MAX_RECONNECT = 3

  function getWsUrl(): string {
    const baseUrl = apiClient.getBaseUrl()
    // http:// → ws://, https:// → wss://
    return baseUrl.replace(/^http/, 'ws') + '/ws/v1/score'
  }

  function connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        const url = getWsUrl()
        ws = new WebSocket(url)
        ws.binaryType = 'arraybuffer'

        ws.onopen = () => {
          isConnected.value = true
          reconnectAttempts = 0
          error.value = null
          resolve()
        }

        ws.onmessage = (event: MessageEvent) => {
          try {
            const data = JSON.parse(
              typeof event.data === 'string' ? event.data : new TextDecoder().decode(event.data)
            )
            lastEvent.value = data
          } catch {
            // 忽略解析错误 (PCM 帧走 binary 通道)
          }
        }

        ws.onerror = () => {
          error.value = 'WebSocket 连接失败'
          reject(new Error('WebSocket connection failed'))
        }

        ws.onclose = (e) => {
          isConnected.value = false
          // 非正常关闭时尝试重连
          if (e.code !== 1000 && reconnectAttempts < MAX_RECONNECT) {
            reconnectAttempts++
            reconnectTimer = setTimeout(() => {
              connect().catch(() => {})
            }, 1000 * reconnectAttempts)
          }
        }
      } catch (e) {
        error.value = `无法创建 WebSocket 连接: ${e}`
        reject(e)
      }
    })
  }

  function sendPcm(pcm: Float32Array): void {
    if (!ws || ws.readyState !== WebSocket.OPEN) return

    // ADR-7: 4字节大端长度前缀
    const lengthPrefix = new Uint8Array(4)
    const len = pcm.length * 4 // Float32 = 4 bytes each
    new DataView(lengthPrefix.buffer).setUint32(0, len, false) // big-endian

    const frame = new Uint8Array(4 + len)
    frame.set(lengthPrefix, 0)
    frame.set(new Uint8Array(pcm.buffer), 4)

    ws.send(frame.buffer)
  }

  function sendControl(type: string, data?: Record<string, any>): void {
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({ type, ...data }))
  }

  function close(): void {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    if (ws) {
      ws.close(1000, 'client disconnect')
      ws = null
    }
    isConnected.value = false
  }

  onBeforeUnmount(() => {
    close()
  })

  return {
    isConnected,
    isLoading,
    lastEvent,
    error,
    connect,
    sendPcm,
    sendControl,
    close,
  }
}
