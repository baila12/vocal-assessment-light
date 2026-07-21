/** 六维分数类型 */

export interface SixDimensionScores {
  pitch: number
  rhythm: number
  breath: number
  technique: number
  muscle_strength: number
  artistry: number
}

export interface ScoreDetail {
  label: string
  grade: string
  score: number
  weight: number       // 权重百分比
  isHeuristic: boolean // ⚠️ 非直接测量 (启发式代理)
  description: string
  subScores?: Record<string, number>
}

export type ScoreLevel = '专业级' | '优秀' | '良好' | '中等' | '及格' | '待改进'
export type ScoreGrade = 'S' | 'A' | 'B' | 'C' | 'D' | 'E'
