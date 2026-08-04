"""评分权重配置 Schema — v7.11 (scoring-config.feature)

GET  /api/v1/scoring/presets      — 默认权重 + 4 风格预设
POST /api/v1/scoring/apply-weights — 纯前端重算: 维度分数 + 权重 → 总分/等级
"""

from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field

from backend.interfaces.api.schemas.common import ApiResponse

# 维度键顺序 — 与 ScoringWeights.components() 一致
DIMENSION_KEYS = ["pitch", "rhythm", "breath", "technique", "muscle", "artistry"]


class ScoringPresetOut(BaseModel):
    """单个风格预设 — name + 中文标签 + 权重"""
    name: str
    label: str
    weights: dict[str, float]


class ScoringPresetsData(BaseModel):
    """GET /scoring/presets 响应数据"""
    default: ScoringPresetOut
    presets: list[ScoringPresetOut]
    default_preset: str


class ScoringPresetsResponse(ApiResponse[ScoringPresetsData]):
    data: Optional[ScoringPresetsData] = None


class ApplyWeightsRequest(BaseModel):
    """POST /scoring/apply-weights 请求

    dimension_scores: 六维原始分数 {pitch..artistry ∈ [0,100]} (来自一次分析结果)
    weights: 自定义权重 {pitch..artistry} (小数, 总和=1.0) — 与 preset 二选一
    preset: 风格预设名 (pop/bel_canto/ethnic/rap) — 与 weights 二选一
    timbre_adjustment: 复用原分析的音色调整值 (可选)
    """
    dimension_scores: dict[str, float] = Field(..., description="六维原始分数")
    weights: Optional[dict[str, float]] = None
    preset: Optional[str] = None
    timbre_adjustment: float = 0.0


class ApplyWeightsData(BaseModel):
    """apply-weights 响应数据"""
    total_score: float = Field(ge=0, le=100)
    level: str
    grade: str
    color: str
    stars: str
    weighted_dimensions: dict[str, float] = Field(default_factory=dict)
    applied_weights: dict[str, float] = Field(default_factory=dict)
    applied_preset: str = "default"


class ApplyWeightsResponse(ApiResponse[ApplyWeightsData]):
    data: Optional[ApplyWeightsData] = None
