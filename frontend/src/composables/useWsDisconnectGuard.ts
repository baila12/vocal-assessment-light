/**
 * useWsDisconnectGuard — WebSocket 断连守卫 (v7.15 H-B15)
 *
 * DEEP_REVIEW H-B15 (HIGH): SingView 录音中 WS 断连时用户完全无感知 —
 *   视图本地 isConnected 不同步 (保持 true), sendPcm 静默丢弃 PCM,
 *   无 toast/无状态变化 → 录音静默丢失数据。
 *
 * 本守卫监听连接状态变化:
 *   1. 始终将 wsIsConnected 同步到 uiIsConnected (双向往来, 单点同步)
 *   2. 仅"连接建立后中途断开" (true→false) 触发 onDisconnect 回调 —
 *      由 wasConnected 门控: 页面初始即未连接 / 显式 close() 不触发。
 *
 * 录音中的断连处理 (停止录音 + 明确告知) 由调用方 onDisconnect 决定,
 * 本守卫只负责检测与门控 — 低耦合, 便于复用与单元测试。
 */
import { watch, type Ref } from 'vue'

export function useWsDisconnectGuard(
  wsIsConnected: Ref<boolean>,
  uiIsConnected: Ref<boolean>,
  onDisconnect: () => void,
): void {
  let wasConnected = false

  watch(wsIsConnected, (connected) => {
    uiIsConnected.value = connected
    if (wasConnected && !connected) {
      onDisconnect()
    }
    wasConnected = connected
  })
}
