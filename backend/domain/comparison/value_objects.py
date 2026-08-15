"""
Comparison 值对象 — v7.3 Phase 1

DDD 对比分析值对象:
  - DimensionComparisonScore: 单维度对比评分 (frozen)
  - ComparisonScores: 四维度聚合评分 (frozen)
"""

from __future__ import annotations
from dataclasses import dataclass, field

# 对比四维风格权重 — 单一数据来源 (v7.19 E1 消双轨)
# 旧值散落于 scoring_engine.py / services.py / value_objects.py 三处, 现统一于此。
COMPARISON_STYLE_WEIGHTS: dict[str, dict[str, float]] = {
    "pop": {"pitch": 0.40, "rhythm": 0.30, "volume": 0.15, "breath": 0.15},
    "classical": {"pitch": 0.50, "rhythm": 0.20, "volume": 0.20, "breath": 0.10},
    "folk": {"pitch": 0.35, "rhythm": 0.25, "volume": 0.20, "breath": 0.20},
    "rap": {"pitch": 0.20, "rhythm": 0.50, "volume": 0.20, "breath": 0.10},
}


@dataclass(frozen=True)
class DimensionComparisonScore:
    """单维度对比评分 — 不可变值对象"""

    score: float = 0.0             # 0-100
    avg_deviation: float = 0.0     # 平均偏差
    max_deviation: float = 0.0     # 最大偏差
    problem_count: int = 0         # 问题帧数量
    details: tuple = ()            # 详细信息 (immutable)


@dataclass(frozen=True)
class ComparisonScores:
    """四维度对比评分聚合 — 不可变值对象

    维度权重单一来源: COMPARISON_STYLE_WEIGHTS['pop'] (v7.19 E1 消双轨)。
    """

    pitch: DimensionComparisonScore = field(default_factory=DimensionComparisonScore)
    rhythm: DimensionComparisonScore = field(default_factory=DimensionComparisonScore)
    volume: DimensionComparisonScore = field(default_factory=DimensionComparisonScore)
    breath: DimensionComparisonScore = field(default_factory=DimensionComparisonScore)
    _confidence: float = 1.0       # 对齐置信度 (内部使用, 0-1)
    _weights: tuple = field(
        default_factory=lambda: tuple(COMPARISON_STYLE_WEIGHTS["pop"].values())
    )  # (pitch, rhythm, volume, breath)

    @property
    def total_score(self) -> float:
        """计算加权总分"""
        return self.weighted_total()

    def weighted_total(self) -> float:
        """计算加权总分 (含置信度修正)

        v7.18 P2 (F4): 温和置信度调制 — 低置信度不归零 (score × (0.5+0.5×conf)),
        避免"对齐不确定"双重惩罚所有维度。
        """
        wp, wr, wv, wb = self._weights
        raw = (
            self.pitch.score * wp
            + self.rhythm.score * wr
            + self.volume.score * wv
            + self.breath.score * wb
        )
        return round(raw * (0.5 + 0.5 * self._confidence), 1)

    def with_confidence(self, confidence: float) -> "ComparisonScores":
        """返回带有新置信度值的不可变副本"""
        return ComparisonScores(
            pitch=self.pitch,
            rhythm=self.rhythm,
            volume=self.volume,
            breath=self.breath,
            _confidence=confidence,
            _weights=self._weights,
        )
