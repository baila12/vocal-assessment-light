"""
Comparison 值对象 — v7.3 Phase 1

DDD 对比分析值对象:
  - DimensionComparisonScore: 单维度对比评分 (frozen)
  - ComparisonScores: 四维度聚合评分 (frozen)
"""

from __future__ import annotations
from dataclasses import dataclass, field


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

    维度权重 (与 scoring_engine.py 保持一致):
      pitch=0.40, rhythm=0.30, volume=0.15, breath=0.15
    """

    pitch: DimensionComparisonScore = field(default_factory=DimensionComparisonScore)
    rhythm: DimensionComparisonScore = field(default_factory=DimensionComparisonScore)
    volume: DimensionComparisonScore = field(default_factory=DimensionComparisonScore)
    breath: DimensionComparisonScore = field(default_factory=DimensionComparisonScore)
    _confidence: float = 1.0       # 对齐置信度 (内部使用, 0-1)
    _weights: tuple = (0.40, 0.30, 0.15, 0.15)  # (pitch, rhythm, volume, breath)

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
