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
    ) -> float:
        """
        计算六维加权总分 + 音色调整。

        Returns:
            float: 最终总分 (clamped [0, 100])
        """
        total = (
            pitch.weighted()
            + rhythm.weighted()
            + breath.weighted()
            + technique.weighted()
            + muscle.weighted()
            + artistry.weighted()
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
        """等级判定: (label, grade, color)"""
        if total_score >= 88:
            return ("专业级", "S", "#22c55e")
        if total_score >= 78:
            return ("优秀", "A", "#3b82f6")
        if total_score >= 62:
            return ("良好", "B", "#10b981")
        if total_score >= 45:
            return ("中等", "C", "#f59e0b")
        if total_score >= 25:
            return ("及格", "D", "#f97316")
        return ("待改进", "E", "#ef4444")
