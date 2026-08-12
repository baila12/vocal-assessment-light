/**
 * useWsDisconnectGuard — 单元测试 (v7.15 H-B15)
 *
 * DEEP_REVIEW H-B15 (HIGH): SingView 录音中 WS 断连时用户完全无感知 —
 *   视图本地 isConnected 不同步 (保持 true), sendPcm 静默丢弃 PCM,
 *   无 toast/无状态变化 → 录音静默丢失数据。
 *
 * 修复: 独立 composable 守卫连接状态 —
 *   1. 始终将 wsManager.isConnected 同步到 UI 本地状态 (true/false)
 *   2. 仅"连接建立后中途断开" (true→false) 触发 onDisconnect (录音中断处理)
 *   页面初始即未连接 / 显式 close 不触发 (wasConnected 门控)
 */

import { ref, nextTick } from 'vue'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useWsDisconnectGuard } from '@/composables/useWsDisconnectGuard'

describe('useWsDisconnectGuard', () => {
  let wsIsConnected: ReturnType<typeof ref<boolean>>
  let uiIsConnected: ReturnType<typeof ref<boolean>>
  let onDisconnect: ReturnType<typeof vi.fn>

  beforeEach(() => {
    wsIsConnected = ref(false)
    uiIsConnected = ref(false)
    onDisconnect = vi.fn()
  })

  it('始终将 UI 连接状态同步到 WS 连接状态', async () => {
    useWsDisconnectGuard(wsIsConnected, uiIsConnected, onDisconnect)

    wsIsConnected.value = true
    await nextTick()
    expect(uiIsConnected.value).toBe(true)

    wsIsConnected.value = false
    await nextTick()
    expect(uiIsConnected.value).toBe(false)
  })

  it('仅在"已连接→断开"转换时触发 onDisconnect', async () => {
    useWsDisconnectGuard(wsIsConnected, uiIsConnected, onDisconnect)

    // 初始未连接 → 连接成功 (false→true): 不触发
    wsIsConnected.value = true
    await nextTick()
    expect(onDisconnect).not.toHaveBeenCalled()

    // 录音中连接断开 (true→false): 触发 (H-B15 核心)
    wsIsConnected.value = false
    await nextTick()
    expect(onDisconnect).toHaveBeenCalledTimes(1)
  })

  it('从未连接时不触发 onDisconnect (页面初始状态)', async () => {
    useWsDisconnectGuard(wsIsConnected, uiIsConnected, onDisconnect)

    wsIsConnected.value = false
    await nextTick()
    wsIsConnected.value = false
    await nextTick()
    expect(onDisconnect).not.toHaveBeenCalled()
  })

  it('每次 true→false 转换各触发一次 (重连后再次断连不丢失)', async () => {
    useWsDisconnectGuard(wsIsConnected, uiIsConnected, onDisconnect)

    wsIsConnected.value = true
    await nextTick()
    wsIsConnected.value = false
    await nextTick() // 第 1 次断连
    expect(onDisconnect).toHaveBeenCalledTimes(1)

    // WS 自动重连 → 再次录音 → 再次断连
    wsIsConnected.value = true
    await nextTick()
    wsIsConnected.value = false
    await nextTick() // 第 2 次断连
    expect(onDisconnect).toHaveBeenCalledTimes(2)
  })
})
