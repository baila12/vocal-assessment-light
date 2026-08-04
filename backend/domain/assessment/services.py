"""
ScoringDomainService — 纯计算，零副作用

六维加权总分 + 音色调整 + 等级判定 + EventBus 发布。
"""

from __future__ import annotations
from backend.shared.event_bus import EventBus
from backend.domain.assessment.events import ScoreCalculated
from backend.domain.assessment.value_objects import (
    PitchScore,
    RhythmScore,
    BreathScore,
    TechniqueScore,
    MuscleStrengthScore,
    ArtistryScore,
    TimbreAdjustment,
)
from backend.domain.assessment.errors import InvalidScoreError
from backend.domain.assessment.scoring_weights import ScoringWeights


class ScoringDomainService:
    """评分领域服务 — Phase 1 实现 EventBus 集成"""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus

    def calculate_total(
        self,
        pitch: PitchScore,
        rhythm: RhythmScore,
        breath: BreathScore,
        technique: TechniqueScore,
        muscle: MuscleStrengthScore,
        artistry: ArtistryScore,
        timbre: TimbreAdjustment | None = None,
        weights: ScoringWeights | None = None,
    ) -> float:
        """
        计算六维加权总分 + 音色调整。

        v7.11: weights 参数 — 权重的单一数据来源 ScoringWeights.
        不传则用默认 v7.4 权重 (13/12/22/25/15/13); 传入则按自定义权重计算
        (支持风格预设 / 用户自定义 / 系统推荐 — scoring-config.feature)。

        Returns:
            float: 最终总分 (clamped [0, 100])
        """
        w = weights or ScoringWeights.default()
        total = w.weighted_total(
            pitch=pitch,
            rhythm=rhythm,
            breath=breath,
            technique=technique,
            muscle=muscle,
            artistry=artistry,
        )

        result = round(timbre.apply(total) if timbre else total, 1)

        # 发布领域事件
        if self._event_bus:
            level, grade, _ = self.determine_level(result)
            self._event_bus.publish(ScoreCalculated(
                total_score=result,
                dimensions={
                    "pitch": pitch.raw_score,
                    "rhythm": rhythm.raw_score,
                    "breath": breath.raw_score,
                    "technique": technique.raw_score,
                    "muscle_strength": muscle.raw_score,
                    "artistry": artistry.raw_score,
                },
                timbre_adjustment=timbre.adjustment if timbre else 0.0,
                level=level,
                grade=grade,
            ))

        return result

    @staticmethod
    def determine_level(total_score: float) -> tuple[str, str, str]:
        """等级判定 — 委托到共享内核 ScoreLevel.from_score() 确保唯一权威来源"""
        from backend.shared.domain_types import ScoreLevel
        level = ScoreLevel.from_score(total_score)
        return (level.label, level.grade, level.color)
