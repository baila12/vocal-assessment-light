/**
 * pitchFps 单元测试 — v7.13 Phase 5 FPS 监控与降级状态机
 *
 * 对齐 pitch-realtime.feature:
 *   - "渲染帧率保障": 满帧率不降级; 持续低帧率自动降至 15fps 目标
 *   - "低性能设备降级": 连续 3s 帧率 < 20fps → 性能模式 + 手动切回画质模式
 */
import { describe, it, expect } from 'vitest'
import { createFpsMonitor } from '@/utils/pitchFps'
import { DEGRADE_TARGET_FPS, LOW_FPS_THRESHOLD } from '@/utils/pitchPlayback'

describe('createFpsMonitor', () => {
  it('初始状态: 0fps, 未降级', () => {
    const m = createFpsMonitor()
    expect(m.getState()).toMatchObject({ currentFps: 0, isDegraded: false, isAutoDegraded: false, consecutiveLowFpsSeconds: 0 })
  })

  it('recordFrame(0) / NaN → no-op (状态不变)', () => {
    const m = createFpsMonitor()
    const before = m.getState()
    m.recordFrame(0)
    m.recordFrame(NaN)
    expect(m.getState()).toEqual(before)
  })

  it('满帧率 (60fps) 持续 → 不降级', () => {
    const m = createFpsMonitor()
    let state = m.getState()
    for (let t = 0; t <= 5000; t += 1000 / 60) {
      state = m.recordFrame(Math.round(t))
    }
    expect(state.isDegraded).toBe(false)
    expect(state.currentFps).toBeGreaterThanOrEqual(50)
  })

  it('低帧率 (10fps) 持续 3s → 自动降级', () => {
    const m = createFpsMonitor()
    let state = m.getState()
    // t=0..2900 → 2.9s 低帧率累计, 未达 3s
    for (let t = 0; t <= 2900; t += 100) {
      state = m.recordFrame(t)
    }
    expect(state.isDegraded).toBe(false)
    // t=3000 → 累计 3.0s → 降级
    state = m.recordFrame(3000)
    expect(state.isDegraded).toBe(true)
    expect(state.isAutoDegraded).toBe(true)
  })

  it('手动恢复画质模式 → 清除降级 (幂等)', () => {
    const m = createFpsMonitor()
    let state = m.getState()
    for (let t = 0; t <= 4000; t += 100) {
      state = m.recordFrame(t)
    }
    expect(state.isDegraded).toBe(true)

    const restored = m.restoreQualityMode()
    expect(restored.isDegraded).toBe(false)
    expect(restored.isAutoDegraded).toBe(false)
    expect(restored.consecutiveLowFpsSeconds).toBe(0)

    // 幂等: 非降级时再次恢复不报错, 状态保持
    const again = m.restoreQualityMode()
    expect(again.isDegraded).toBe(false)
  })

  it('resetTime 保留降级状态但重置时间基准 (后台恢复不误降级)', () => {
    const m = createFpsMonitor()
    // 制造降级 (10fps 持续 3s)
    for (let t = 0; t <= 3000; t += 100) m.recordFrame(t)
    expect(m.getState().isDegraded).toBe(true)

    // 长时间停顿 (间隙 6s) → resetTime(9000): 清窗口/连段, 保留降级
    const after = m.resetTime(9000)
    expect(after.isDegraded).toBe(true)
    expect(after.isAutoDegraded).toBe(true)
    expect(after.currentFps).toBe(0)
    expect(after.consecutiveLowFpsSeconds).toBe(0)

    // 恢复后下一帧 dtMs 仅 16ms → 连段 ≈0.016s, 不把 6s 间隙误计为持续低帧率
    const next = m.recordFrame(9016)
    expect(next.consecutiveLowFpsSeconds).toBeLessThan(1)
    expect(next.isDegraded).toBe(true) // 已降级状态不被 resetTime 清除
  })

  it('帧率回升后低帧率累计清零', () => {
    const m = createFpsMonitor()
    // 1s 低帧率 → 累计 ~1s
    for (let t = 0; t <= 1000; t += 100) m.recordFrame(t)
    expect(m.getState().consecutiveLowFpsSeconds).toBeGreaterThanOrEqual(0.9)
    // 切回 60fps 1s → 清零
    for (let t = 1100; t <= 2100; t += 1000 / 60) m.recordFrame(Math.round(t))
    expect(m.getState().consecutiveLowFpsSeconds).toBe(0)
  })

  it('返回不可变快照 (每次新对象, 不共享引用)', () => {
    const m = createFpsMonitor()
    const s1 = m.getState()
    const s2 = m.getState()
    expect(s1).not.toBe(s2)
    expect(s1).toEqual(s2)
  })

  it('降级目标为 15fps, 触发阈值为 20fps (常量断言)', () => {
    expect(DEGRADE_TARGET_FPS).toBe(15)
    expect(LOW_FPS_THRESHOLD).toBe(20)
  })
})
