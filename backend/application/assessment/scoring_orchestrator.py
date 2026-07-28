"""
评分编排器 — v7.1 Phase B

统一评分入口: 从旧 AudioFeaturesResult 到 DDD 六维度评分 → 生产可用的 dict 格式。

设计原则:
- 绞杀者模式: 编排器可独立使用，也可通过 analyze_and_score() 注入
- Flag 门控: enable_ddd_scoring 控制新旧路径切换 (默认启用)
- 特征桥接: 通过 FeatureAdapterRegistry 将旧 DTO 映射到 DDD 特征
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
from backend.application.assessment.feature_adapters import FeatureAdapterRegistry
from backend.shared.event_bus import EventBus
from backend.shared.domain_types import ScoreLevel

logger = logging.getLogger(__name__)


class ScoringOrchestrator:
    """
    评分编排器 — 绞杀者模式下统一评分入口。

    用法:
        orchestrator = ScoringOrchestrator(event_bus=bus)
        result_dict = orchestrator.calculate(old_features, is_clean_vocal=False)

    返回:
        dict 与旧 ScoreServiceV4 兼容:
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

        # 特征适配器
        self._adapters = FeatureAdapterRegistry()

    def calculate(
        self,
        features,  # AudioFeaturesResult
        is_clean_vocal: bool = False,
        voice_quality_score: float = 100.0,
    ) -> dict:
        """
        计算六维评分。

        Args:
            features: AudioFeaturesResult (旧 DTO)
            is_clean_vocal: 是否为纯净人声 (Demucs 分离后)
            voice_quality_score: 人声质量分数 (0-100)

        Returns:
            dict: 六维评分结果 (兼容旧 ScoreServiceV4 格式)
        """
        result: dict = {}
        heuristic_dimensions: list[str] = []

        # 逐个维度评分 (每个维度独立可开关)
        # 1. 音准 (10%)
        pitch_score = self._score_pitch(features) if self._flags.enable_pitch else None
        result["pitch_score"] = pitch_score.raw_score if pitch_score else 0.0

        # 2. 节奏 (10%)
        rhythm_score = self._score_rhythm(features, is_clean_vocal) if self._flags.enable_rhythm else None
        result["rhythm_score"] = rhythm_score.raw_score if rhythm_score else 0.0

        # 3. 气息 (20%)
        breath_score = self._score_breath(features) if self._flags.enable_breath else None
        result["breath_score"] = breath_score.raw_score if breath_score else 0.0

        # 4. 发声技术 (25%) — 咬字 + 气声比
        technique_score = self._score_technique(features) if self._flags.enable_technique else None
        result["technique_score"] = technique_score.raw_score if technique_score else 0.0

        # 5. 肌肉力量 (25%) — ⚠️ HEURISTIC
        muscle_score = self._score_muscle(features) if self._flags.enable_muscle_strength else None
        result["muscle_strength_score"] = muscle_score.raw_score if muscle_score else 0.0
        if self._flags.enable_muscle_strength:
            heuristic_dimensions.append("muscle_strength")

        # 6. 艺术表现 (10%)
        artistry_score = self._score_artistry(features) if self._flags.enable_artistry else None
        result["artistry_score"] = artistry_score.raw_score if artistry_score else 0.0

        # 音色加减分 (不属于六维)
        timbre = self._score_timbre(features) if self._flags.enable_timbre_adjustment else None
        result["timbre_adjustment"] = timbre.adjustment if timbre else 0.0
        if self._flags.enable_timbre_adjustment:
            heuristic_dimensions.append("timbre")

        # 计算加权总分
        result["total_score"] = self._domain_service.calculate_total(
            pitch=pitch_score,
            rhythm=rhythm_score,
            breath=breath_score,
            technique=technique_score,
            muscle=muscle_score,
            artistry=artistry_score,
            timbre=timbre,
        )

        # 等级判定 (唯一权威来源)
        level = ScoreLevel.from_score(result["total_score"])
        result["level"] = level.label
        result["grade"] = level.grade
        result["color"] = level.color
        result["stars"] = self._stars_for_score(result["total_score"])
        result["heuristic_dimensions"] = heuristic_dimensions

        # 诊断信息
        result["pitch_diagnosis"] = self._make_diagnosis(pitch_score, "mae_cents")
        result["rhythm_diagnosis"] = self._make_diagnosis(rhythm_score, "deviation_ratio")
        result["breath_diagnosis"] = self._make_diagnosis(breath_score)
        result["technique_diagnosis"] = self._make_diagnosis(technique_score)
        result["artistry_diagnosis"] = self._make_diagnosis(artistry_score)

        # 兼容旧字段
        result["critical_issues"] = []
        result["is_disqualified"] = False
        result["pitch"] = result["pitch_score"]
        result["rhythm"] = result["rhythm_score"]
        result["breath"] = result["breath_score"]
        result["emotion"] = result["artistry_score"]
        result["volume"] = self._compute_volume(features)
        result["total"] = result["total_score"]

        # 人声质量惩罚
        if voice_quality_score < 30:
            result["total_score"] = min(result["total_score"], 40)
            result["critical_issues"].append("人声质量极差，总分上限40分")
        elif voice_quality_score < 50:
            penalty = (50 - voice_quality_score) / 50 * 35
            result["total_score"] = max(0, result["total_score"] - penalty)

        return result

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

    def _score_pitch(self, features) -> 'PitchScore':
        try:
            pf = self._adapters.to_pitch(features)
            return self._pitch_scorer.calculate(pf)
        except Exception as e:
            logger.warning("Pitch scoring failed: %s, using defaults", e)
            from backend.domain.assessment.value_objects import PitchScore
            return PitchScore(raw_score=50.0, mae_cents=40.0, rpa=0.5, rca=0.5,
                              gross_error_rate=0.1, octave_error_rate=0.0,
                              smoothness_cv=2.0, detection_rate=1.0, pitch_breaks=0)

    def _score_rhythm(self, features, is_clean_vocal: bool) -> 'RhythmScore':
        try:
            rf = self._adapters.to_rhythm(features, is_clean_vocal)
            return self._rhythm_scorer.calculate(rf)
        except Exception as e:
            logger.warning("Rhythm scoring failed: %s, using defaults", e)
            from backend.domain.assessment.value_objects import RhythmScore
            return RhythmScore(raw_score=50.0, onset_cv=1.0,
                               median_ioi_deviation=0.1, irregularity_penalty=0.0,
                               is_clean_vocal=is_clean_vocal)

    def _score_breath(self, features) -> 'BreathScore':
        try:
            bf = self._adapters.to_breath(features)
            return self._breath_scorer.calculate(bf)
        except Exception as e:
            logger.warning("Breath scoring failed: %s, using defaults", e)
            from backend.domain.assessment.value_objects import BreathScore
            return BreathScore(raw_score=50.0, long_note_support=50.0,
                               dynamic_control=50.0, breath_design=50.0,
                               breath_technique=50.0, is_clean_vocal=False,
                               hnr_stability=15.0, dynamic_range_db=15.0)

    def _score_technique(self, features) -> 'TechniqueScore':
        try:
            tf = self._adapters.to_technique(features)
            return self._technique_scorer.calculate(tf)
        except Exception as e:
            logger.warning("Technique scoring failed: %s, using defaults", e)
            from backend.domain.assessment.value_objects import TechniqueScore
            return TechniqueScore(raw_score=50.0, articulation_clarity=50.0,
                                  breath_voice_ratio=50.0, hnr_mean=15.0, cpp_mean=1.0)

    def _score_muscle(self, features) -> 'MuscleStrengthScore':
        try:
            mf = self._adapters.to_muscle(features)
            return self._muscle_scorer.calculate(mf)
        except Exception as e:
            logger.warning("Muscle scoring failed: %s, using defaults", e)
            from backend.domain.assessment.value_objects import MuscleStrengthScore
            return MuscleStrengthScore(raw_score=50.0, body_muscle_strength=50.0,
                                        facial_muscle_strength=50.0,
                                        is_heuristic=True)

    def _score_artistry(self, features) -> 'ArtistryScore':
        try:
            af = self._adapters.to_artistry(features)
            return self._artistry_scorer.calculate(af)
        except Exception as e:
            logger.warning("Artistry scoring failed: %s, using defaults", e)
            from backend.domain.assessment.value_objects import ArtistryScore
            return ArtistryScore(raw_score=50.0, vibrato_quality=50.0,
                                 dynamic_control=50.0, phrase_expression=50.0,
                                 pitch_variation=50.0)

    def _score_timbre(self, features) -> 'TimbreAdjustment':
        try:
            tf = self._adapters.to_timbre(features)
            return self._timbre_adjuster.calculate(tf)
        except Exception as e:
            logger.warning("Timbre scoring failed: %s, using defaults", e)
            from backend.domain.assessment.value_objects import TimbreAdjustment
            return TimbreAdjustment(adjustment=0.0, brightness_score=0.5,
                                    warmth_score=0.5, nasality_score=0.0,
                                    confidence=0.0, is_heuristic=True)

    # ================================================================
    # 辅助方法
    # ================================================================

    @staticmethod
    def _stars_for_score(total: float) -> str:
        if total >= 88: return "★★★"
        if total >= 78: return "★★☆"
        if total >= 62: return "★★"
        if total >= 45: return "★☆"
        if total >= 25: return "★"
        return "☆"

    @staticmethod
    def _compute_volume(features) -> float:
        bs = getattr(features, 'breath_stability', None)
        if bs is None:
            return 50.0
        dr = getattr(bs, 'dynamic_range', 15.0)
        dr = float(dr) if dr else 15.0
        if dr > 30:
            return min(100, 80 + (dr - 30) * 0.5)
        elif dr > 15:
            return 50 + (dr - 15) * 2.0
        elif dr > 5:
            return 20 + (dr - 5) * 3.0
        else:
            return max(5, dr * 4)

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
