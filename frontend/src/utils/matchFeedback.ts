/**
 * 自动匹配结果 → 用户反馈 — 纯函数 (v7.15 H-B14)
 *
 * DEEP_REVIEW H-B14 (HIGH): songMatch.store.error 在 matchAudio 失败时记录,
 *   但视图从不读取 → 网络/服务端错误静默吞掉。
 *
 * 统一评估匹配后的三种可观测状态, 错误优先级最高:
 *   store.error      → error   (此前被静默吞掉的场景, H-B14 修复核心)
 *   matchedSong      → matched
 *   fallbackReason   → fallback (优雅回退, 非错误)
 *   均无             → none
 */

export interface MatchOutcome {
  matchedSongTitle: string | null
  fallbackReason: string
  error: string | null
}

export type MatchFeedback =
  | { kind: 'error'; message: string }
  | { kind: 'matched'; title: string }
  | { kind: 'fallback' }
  | { kind: 'none' }

export function evaluateMatchResult(outcome: MatchOutcome): MatchFeedback {
  if (outcome.error) {
    return { kind: 'error', message: outcome.error }
  }
  if (outcome.matchedSongTitle) {
    return { kind: 'matched', title: outcome.matchedSongTitle }
  }
  if (outcome.fallbackReason) {
    return { kind: 'fallback' }
  }
  return { kind: 'none' }
}
