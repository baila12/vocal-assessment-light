/**
 * evaluateMatchResult — 单元测试 (v7.15 H-B14)
 *
 * DEEP_REVIEW H-B14 (HIGH): songMatch.store.error 在 matchAudio 失败时记录,
 *   但 CompareView.startAutoMatch 从不读取 → 网络/服务端错误用户完全无感知
 *   (死信 ref: 全仓无任何读取点)。
 *
 * 修复: 纯函数统一评估匹配结果, 错误优先级最高 —
 *   store.error 存在 → 错误反馈 (此前被静默吞掉)
 *   否则 matchedSong → 匹配成功
 *   否则 fallbackReason → 优雅回退
 *   否则 → 无反馈
 */
import { describe, it, expect } from 'vitest'
import { evaluateMatchResult } from '@/utils/matchFeedback'

describe('evaluateMatchResult', () => {
  it('有 error → 返回错误反馈 (H-B14 核心: 错误优先可见)', () => {
    const result = evaluateMatchResult({
      matchedSongTitle: '月亮代表我的心',
      fallbackReason: '',
      error: 'network error',
    })
    expect(result).toEqual({ kind: 'error', message: 'network error' })
  })

  it('无 error + 有匹配 → 匹配成功反馈', () => {
    const result = evaluateMatchResult({
      matchedSongTitle: '月亮代表我的心',
      fallbackReason: '',
      error: null,
    })
    expect(result).toEqual({ kind: 'matched', title: '月亮代表我的心' })
  })

  it('无 error + 无匹配 + 有 fallback → 优雅回退反馈', () => {
    const result = evaluateMatchResult({
      matchedSongTitle: null,
      fallbackReason: 'no_match',
      error: null,
    })
    expect(result).toEqual({ kind: 'fallback' })
  })

  it('全部为空 → 无反馈', () => {
    const result = evaluateMatchResult({
      matchedSongTitle: null,
      fallbackReason: '',
      error: null,
    })
    expect(result).toEqual({ kind: 'none' })
  })

  it('error 优先于匹配成功 (失败后残留 matchedSong 不掩盖错误)', () => {
    const result = evaluateMatchResult({
      matchedSongTitle: '旧匹配',
      fallbackReason: '',
      error: '500 server error',
    })
    expect(result.kind).toBe('error')
    expect(result.message).toBe('500 server error')
  })

  it('error 优先于 fallback', () => {
    const result = evaluateMatchResult({
      matchedSongTitle: null,
      fallbackReason: 'no_match',
      error: 'upload failed',
    })
    expect(result.kind).toBe('error')
  })
})
