"""评分权重配置路由 — v7.11 (scoring-config.feature)

GET  /api/v1/scoring/presets       — 默认权重 + 4 风格预设 (流行/美声/民族/说唱)
POST /api/v1/scoring/apply-weights — 维度分数 + 权重 → 总分/等级 (纯前端重算, 不上传)

设计:
    - 权重单一数据来源 ScoringWeights (领域值对象)
    - 校验委托 domain validate() — 总和 100% + 单维 ≤50%
    - 等级判定委托 ScoreLevel (唯一权威来源)
"""

from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException

from backend.domain.assessment.scoring_weights import ScoringWeights, WeightsValidationError
from backend.shared.domain_types import ScoreLevel
from backend.interfaces.api.schemas.scoring import (
    ApplyWeightsRequest,
    ApplyWeightsResponse,
    ApplyWeightsData,
    ScoringPresetsResponse,
    ScoringPresetsData,
    ScoringPresetOut,
)

logger = logging.getLogger(__name__)
router = APIRouter()

# 预设中文标签 (展示层)
_PRESET_LABELS = {
    "pop": "流行",
    "bel_canto": "美声",
    "ethnic": "民族",
    "rap": "说唱",
}


def _preset_out(name: str, weights: ScoringWeights, label: str) -> ScoringPresetOut:
    return ScoringPresetOut(name=name, label=label, weights=weights.to_dict())


@router.get("/scoring/presets", response_model=ScoringPresetsResponse)
async def get_scoring_presets():
    """返回默认权重 + 4 风格预设 — 前端权重面板数据源."""
    presets = [
        _preset_out(name, w, _PRESET_LABELS.get(name, name))
        for name, w in ScoringWeights.presets().items()
    ]
    data = ScoringPresetsData(
        default=_preset_out("default", ScoringWeights.default(), "默认 (v7.4)"),
        presets=presets,
        default_preset=ScoringWeights.default_preset_name(),
    )
    return ScoringPresetsResponse(data=data)


@router.post("/scoring/apply-weights", response_model=ApplyWeightsResponse)
async def apply_weights(req: ApplyWeightsRequest):
    """用指定权重对既有维度分数重新计算总分 — 支持预设或自定义权重.

    纯前端重算 (scoring-config.feature: "点击其他预设后 → 用新权重重新计算总分")。
    不重新分析音频, 不触发评分管线。
    """
    # ---- 权重解析: preset / weights / 默认 三选一 ----
    if req.preset and req.weights:
        raise HTTPException(status_code=400, detail="preset 和 weights 只能二选一")

    applied_preset = "default"
    try:
        if req.weights is not None:
            weights = ScoringWeights.from_dict(req.weights)
        elif req.preset is not None:
            weights = ScoringWeights.from_preset(req.preset)
            applied_preset = req.preset
        else:
            weights = ScoringWeights.default()
    except WeightsValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # ---- 维度分数校验 ----
    scores = req.dimension_scores
    missing = [k for k in ["pitch", "rhythm", "breath", "technique", "muscle", "artistry"]
               if k not in scores]
    if missing:
        raise HTTPException(status_code=400, detail=f"缺少维度分数: {', '.join(missing)}")

    # ---- 计算加权总分 ----
    total = weights.weighted_total_from_scores(scores)
    # 音色调整: 复用原分析值, 夹取 [-5, +3]
    clamped_adj = max(-5.0, min(3.0, req.timbre_adjustment))
    total = max(0.0, min(100.0, total + clamped_adj))
    total = round(total, 1)

    level = ScoreLevel.from_score(total)
    weighted_dimensions = {
        k: round(scores[k] * getattr(weights, k), 1)
        for k in ["pitch", "rhythm", "breath", "technique", "muscle", "artistry"]
    }

    data = ApplyWeightsData(
        total_score=total,
        level=level.label,
        grade=level.grade,
        color=level.color,
        stars=_stars_for_score(total),
        weighted_dimensions=weighted_dimensions,
        applied_weights=weights.to_dict(),
        applied_preset=applied_preset,
    )
    return ApplyWeightsResponse(data=data)


def _stars_for_score(total: float) -> str:
    if total >= 88:
        return "★★★"
    if total >= 78:
        return "★★☆"
    if total >= 62:
        return "★★"
    if total >= 45:
        return "★☆"
    if total >= 25:
        return "★"
    return "☆"
