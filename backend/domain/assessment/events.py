"""评分领域事件 — Phase 1 实现 EventBus 触发"""

from __future__ import annotations
from dataclasses import dataclass, field
from backend.shared.event_bus import DomainEvent


@dataclass(frozen=True)
class ScoreCalculated(DomainEvent):
    """评分完成事件 — 每次 calculate_total() 成功后发布"""

    total_score: float
    dimensions: dict[str, float]  # pitch, rhythm, breath, technique, muscle_strength, artistry
    timbre_adjustment: float = 0.0
    level: str = ""
    grade: str = ""


@dataclass(frozen=True)
class DimensionAnalyzed(DomainEvent):
    """单维度分析完成事件"""

    dimension: str  # pitch / rhythm / breath / technique / muscle_strength / artistry
    raw_score: float
    is_heuristic: bool = False
    analysis_id: str = ""
