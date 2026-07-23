/**
 * 评分颜色工具 — v7.0.2
 *
 * 从 SingView/CompareView/ScoreCard/ReportView 提取共享颜色逻辑，
 * 消除代码重复 (LOW优先级修复)。
 */

/**
 * 根据分数返回对应颜色 (六维等级体系)
 * S(88+): 绿色, A(78+): 蓝色, B(62+): 蓝绿
 * C(45+): 琥珀, D(25+): 橙, E(<25): 红
 */
export function scoreColor(score: number): string {
  if (score >= 88) return '#22c55e'
  if (score >= 78) return '#3b82f6'
  if (score >= 62) return '#10b981'
  if (score >= 45) return '#f59e0b'
  if (score >= 25) return '#f97316'
  return '#ef4444'
}

/**
 * 对比分析专用: 更宽松的阈值
 * 80+: 成功色, 60+: 警告色, <60: 危险色
 */
export function matchColor(rate: number): string {
  if (rate >= 80) return 'var(--el-color-success)'
  if (rate >= 60) return 'var(--el-color-warning)'
  return 'var(--el-color-danger)'
}
