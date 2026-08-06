/** API 响应类型 — 手动维护，openapi-typescript 自动生成为补充 */

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
  /** v7.8: 后端详细字段 (列表端点可能不返回) */
  filepath?: string | null
  advice?: string[]
  scores?: Record<string, number>
}

export interface HistoryListResponse {
  history: HistoryRecord[]
  total: number
  page: number
  /** v7.8: 后端分页元数据 (GET /api/v1/history 始终返回) */
  total_pages: number
  limit: number
}

/** v7.10: 标准歌曲库 — 歌曲难度 (后端枚举) */
export type Difficulty = 'beginner' | 'intermediate' | 'advanced'

/** v7.10: 标准歌曲库 — 歌曲风格 (后端枚举) */
export type SongStyle = 'pop' | 'classical' | 'folk' | 'rap'

/** v7.10: 歌曲元数据 (嵌套在 SongRecord 内) */
export interface SongMetadata {
  title: string
  artist: string
  key: string
  bpm: number
  difficulty: Difficulty
  style: SongStyle
  /** v7.12: 音域 (如 "C3-E5"); '' = 未知 */
  vocal_range: string
}

/** v7.10: 歌曲记录 (对齐后端 SongOut) */
export interface SongRecord {
  id: string
  metadata: SongMetadata
  /** 绝对文件系统路径; 无音频时为空字符串 */
  filepath: string
  duration_seconds: number
  feature_status: 'pending' | 'preparing' | 'ready' | 'failed'
  scoring_config: Record<string, unknown>
  created_at: string
}

/** v7.10: 创建歌曲响应 */
export interface SongCreateResponse {
  success: boolean
  song: SongRecord
}

/** v7.10: 歌曲列表响应 — 后端不返回 total_pages, 需前端 Math.ceil(total/limit) */
export interface SongListResponse {
  success: boolean
  songs: SongRecord[]
  total: number
  page: number
  limit: number
}

/** v7.10: 歌曲详情响应 */
export interface SongDetailResponse {
  success: boolean
  song: SongRecord
}

/** v7.10: 删除歌曲响应 */
export interface SongDeleteResponse {
  success: boolean
  deleted: boolean
}

/** v7.11: 六维权重 (小数, 总和=1.0) — 对齐后端 ScoringWeights */
export interface ScoringWeightsDto {
  pitch: number
  rhythm: number
  breath: number
  technique: number
  muscle: number
  artistry: number
}

/** v7.11: 风格预设 (GET /api/v1/scoring/presets 项) */
export interface ScoringPreset {
  name: string
  label: string
  weights: ScoringWeightsDto
}

/** v7.11: presets 响应数据 */
export interface ScoringPresetsData {
  default: ScoringPreset
  presets: ScoringPreset[]
  default_preset: string
}

export interface ScoringPresetsResponse {
  success: boolean
  data: ScoringPresetsData
  error?: string
}

/** v7.11: apply-weights 请求/响应 (POST /api/v1/scoring/apply-weights) */
export interface ApplyWeightsRequest {
  dimension_scores: Record<string, number>
  weights?: ScoringWeightsDto
  preset?: string
  timbre_adjustment?: number
}

export interface ApplyWeightsData {
  total_score: number
  level: string
  grade: string
  color: string
  stars: string
  weighted_dimensions: Record<string, number>
  applied_weights: ScoringWeightsDto
  applied_preset: string
}

export interface ApplyWeightsResponse {
  success: boolean
  data: ApplyWeightsData
  error?: string
}
