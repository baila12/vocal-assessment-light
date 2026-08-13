"""
评分编排器 — v7.1 Phase B (v7.16 P2-15: 死 calculate() 路径已移除)

统一评分入口: 消费 DDD Features → 六维度评分 → 生产可用的 dict 格式。

设计原则:
- 单一评分路径: calculate_ddd() 为唯一生产路径 (v7.16 移除旧 calculate())
- Flag 门控: enable_ddd_scoring 控制维度开关 (默认启用)
"""

from __future__ import annotations
import logging
from typing import Optional, TYPE_CHECKING

from backend.domain.assessment.services import ScoringDomainService
from backend.domain.assessment.pitch_scorer import PitchScorer, PitchFeatures
from backend.domain.assessment.rhythm_scorer import RhythmScorer, RhythmFeatures
from backend.domain.assessment.breath_scorer import BreathScorer, BreathFeatures
from backend.domain.assessment.technique_scorer import TechniqueScorer, TechniqueFeatures
from backend.domain.assessment.muscle_scorer import MuscleStrengthScorer, MuscleFeatures
from backend.domain.assessment.artistry_scorer import ArtistryScorer, ArtistryFeatures
from backend.domain.assessment.timbre_adjuster import TimbreAdjuster, TimbreFeatures
from backend.domain.assessment.feature_flags import DimensionFlags
from backend.shared.event_bus import EventBus
from backend.shared.domain_types import ScoreLevel

logger = logging.getLogger(__name__)
# 设计上恒为启发式的维度 — 不视为失败, 不产生 scoring_warnings
_DESIGN_HEURISTIC_KEYS = {"muscle_strength", "timbre"}


class ScoringOrchestrator:
    """
    评分编排器 — DDD 原生评分入口。

    用法:
        orchestrator = ScoringOrchestrator(event_bus=bus)
        result_dict = orchestrator.calculate_ddd(
            pitch=..., rhythm=..., breath=..., technique=...,
            muscle=..., artistry=..., timbre=..., audiofeat=...,
        )

    返回:
        dict (六维评分 + 总分 + 等级):
        {
            "pitch_score": float,
            "rhythm_score": float,
            "breath_score": float,
            "technique_score": float,
            "muscle_strength_score": float,
            "artistry_score": float,
            "total_score": float,
            "timbre_adjustment": float,
            "level": str,
            "grade": str,
            "stars": str,
            "color": str,
            "heuristic_dimensions": [str],
            "pitch_diagnosis": {...},
            "rhythm_diagnosis": {...},
            ...
        }
    """

    def __init__(
        self,
        event_bus: EventBus | None = None,
        flags: DimensionFlags | None = None,
    ) -> None:
        self._event_bus = event_bus
        self._flags = flags or DimensionFlags()

        # 初始化 DDD 评分器 (纯计算, 无副作用)
        self._pitch_scorer = PitchScorer()
        self._rhythm_scorer = RhythmScorer()
        self._breath_scorer = BreathScorer()
        self._technique_scorer = TechniqueScorer()
        self._muscle_scorer = MuscleStrengthScorer()
        self._artistry_scorer = ArtistryScorer()
        self._timbre_adjuster = TimbreAdjuster()
        self._domain_service = ScoringDomainService(event_bus=event_bus)

    def calculate_ddd(
        self,
        pitch: PitchFeatures | None = None,
        rhythm: RhythmFeatures | None = None,
        breath: BreathFeatures | None = None,
        technique: TechniqueFeatures | None = None,
        muscle: MuscleFeatures | None = None,
        artistry: ArtistryFeatures | None = None,
        timbre: TimbreFeatures | None = None,
        audiofeat: 'AudiofeatFeatures | None' = None,
        voice_quality_score: float = 100.0,
    ) -> dict:
        """
        DDD 原生评分路径 — 直接消费 DDD Features, 绕过 FeatureAdapterRegistry.

        用法:
            features = ddd_orchestrator.extract_all(y, sr, f0, voiced)
            score = scoring_orch.calculate_ddd(
                pitch=features.pitch, rhythm=features.rhythm, ...,
                audiofeat=features.audiofeat,
            )

        v7.3: audiofeat 可选增强 — 传入 AudiofeatFeatures 以精化评分
        """
        result: dict = {}
        heuristic_dimensions: list[str] = []

        # 1. 音准 (10%)
        if self._flags.enable_pitch and pitch is not None:
            ps = self._pitch_scorer.calculate(pitch)
        else:
            from backend.domain.assessment.value_objects import PitchScore
            ps = PitchScore(raw_score=0.0, mae_cents=0.0, rpa=0.0, rca=0.0,
                           gross_error_rate=0.0, octave_error_rate=0.0,
                           smoothness_cv=2.0, detection_rate=1.0, pitch_breaks=0)
        result["pitch_score"] = ps.raw_score

        # 2. 节奏 (10%)
        if self._flags.enable_rhythm and rhythm is not None:
            rs = self._rhythm_scorer.calculate(rhythm)
        else:
            from backend.domain.assessment.value_objects import RhythmScore
            rs = RhythmScore(raw_score=0.0, onset_cv=1.0,
                            median_ioi_deviation=0.1, irregularity_penalty=0.0,
                            is_clean_vocal=False)
        result["rhythm_score"] = rs.raw_score

        # 3. 气息 (20%)
        if self._flags.enable_breath and breath is not None:
            bs = self._breath_scorer.calculate(breath, audiofeat=audiofeat)
        else:
            from backend.domain.assessment.value_objects import BreathScore
            bs = BreathScore(raw_score=0.0, long_note_support=0.0, dynamic_control=0.0,
                           breath_design=0.0, breath_technique=0.0, is_clean_vocal=False,
                           hnr_stability=15.0, dynamic_range_db=0.0)
        result["breath_score"] = bs.raw_score

        # 4. 发声技术 (25%)
        if self._flags.enable_technique and technique is not None:
            ts = self._technique_scorer.calculate(technique, audiofeat=audiofeat)
        else:
            from backend.domain.assessment.value_objects import TechniqueScore
            ts = TechniqueScore(raw_score=0.0, articulation_clarity=0.0,
                              breath_voice_ratio=0.0, hnr_mean=0.0, cpp_mean=0.0)
        result["technique_score"] = ts.raw_score

        # 5. 肌肉力量 (25%) ⚠️ HEURISTIC
        if self._flags.enable_muscle_strength and muscle is not None:
            ms = self._muscle_scorer.calculate(muscle, audiofeat=audiofeat)
            heuristic_dimensions.append("muscle_strength")
        else:
            from backend.domain.assessment.value_objects import MuscleStrengthScore
            ms = MuscleStrengthScore(raw_score=0.0, body_muscle_strength=0.0,
                                    facial_muscle_strength=0.0, is_heuristic=True)
        result["muscle_strength_score"] = ms.raw_score

        # 6. 艺术表现 (10%)
        if self._flags.enable_artistry and artistry is not None:
            ars = self._artistry_scorer.calculate(artistry)
        else:
            from backend.domain.assessment.value_objects import ArtistryScore
            ars = ArtistryScore(raw_score=0.0, vibrato_quality=0.0,
                              dynamic_control=0.0, phrase_expression=0.0, pitch_variation=0.0)
        result["artistry_score"] = ars.raw_score

        # 音色加减分
        if self._flags.enable_timbre_adjustment and timbre is not None:
            ta = self._timbre_adjuster.calculate(timbre, audiofeat=audiofeat)
            heuristic_dimensions.append("timbre")
        else:
            from backend.domain.assessment.value_objects import TimbreAdjustment
            ta = TimbreAdjustment(adjustment=0.0, brightness_score=0.0,
                                warmth_score=0.0, nasality_score=0.0,
                                confidence=0.0, is_heuristic=True)
        result["timbre_adjustment"] = ta.adjustment

        # 加权总分
        result["total_score"] = self._domain_service.calculate_total(
            pitch=ps, rhythm=rs, breath=bs, technique=ts,
            muscle=ms, artistry=ars, timbre=ta,
        )

        # v7.14 审查 6.3: calculate_ddd 无 50.0 fallback (失败直接冒泡), 恒空
        result["scoring_warnings"] = []

        # 等级判定
        level = ScoreLevel.from_score(result["total_score"])
        result["level"] = level.label
        result["grade"] = level.grade
        result["color"] = level.color
        result["stars"] = self._stars_for_score(result["total_score"])
        result["heuristic_dimensions"] = heuristic_dimensions

        # 兼容字段
        result["pitch"] = result["pitch_score"]
        result["rhythm"] = result["rhythm_score"]
        result["breath"] = result["breath_score"]
        result["emotion"] = result["artistry_score"]
        result["volume"] = 50.0
        result["total"] = result["total_score"]
        result["critical_issues"] = []
        result["is_disqualified"] = False

        # 人声质量惩罚
        if voice_quality_score < 30:
            result["total_score"] = min(result["total_score"], 40)

        return result

    # ================================================================
    # 各维度评分 (内部方法)
    # ================================================================

    # ================================================================
    # 辅助方法
    # ================================================================

    @staticmethod

    @staticmethod
    def _stars_for_score(total: float) -> str:
        if total >= 88: return "★★★"
        if total >= 78: return "★★☆"
        if total >= 62: return "★★"
        if total >= 45: return "★☆"
        if total >= 25: return "★"
        return "☆"

    @staticmethod

    @staticmethod
    def _make_diagnosis(score_obj, extra_field: str | None = None) -> dict:
        if score_obj is None:
            return {"score": 0.0, "level": "待改进", "issues": [], "suggestions": []}

        raw = float(getattr(score_obj, 'raw_score', 0))
        level = ScoreLevel.from_score(raw)
        diagnosis = getattr(score_obj, 'diagnosis', ())
        result = {
            "score": raw,
            "level": level.label,
            "issues": list(diagnosis) if diagnosis else [],
            "suggestions": [],
        }
        if extra_field:
            result[extra_field] = getattr(score_obj, extra_field, 0.0)
        return result
