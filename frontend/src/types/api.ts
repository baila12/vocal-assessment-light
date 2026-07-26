/** API 响应类型 — 手动维护，openapi-typescript 自动生成为补充 */

export interface ApiResponse<T> {
  success: boolean
  data: T
}

export interface ErrorResponse {
  success: false
  error: string
  detail?: string
}

/** Phase 4: 完整六维评分响应类型 */
export interface AssessmentResult {
  analysis_id: string
  total_score: number
  scores: {
    pitch: number
    rhythm: number
    breath: number
    technique: number
    muscle_strength: number
    artistry: number
  }
  timbre_adjustment: number
  level: string
  grade: string
  advice: string[]
  mode: 'quick' | 'professional'
  is_voice: boolean
  filepath: string | null
  basic_info: Record<string, unknown> | null
  heuristic_dimensions: string[]
  normalization: {
    applied: boolean
    note: string
  }
}

export interface HistoryRecord {
  id: number
  filename: string
  mode: string
  total_score: number
  level: string
  grade: string
  created_at: string
  duration: number
}

export interface HistoryListResponse {
  records: HistoryRecord[]
  total: number
  page: number
}
