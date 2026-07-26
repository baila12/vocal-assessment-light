"""
艺术表现评分器 v7.0 — 移植 v6.1 独立声学特征

四个子维度:
  - 颤音品质 (vibrato_quality): 30%
  - 动态控制 (dynamic/crescendo): 30%
  - 乐句处理 (phrase/artistic_fluctuation): 25%
  - 音高变化 (pitch_variation): 15%

文献: Sundberg (1987), Canazza et al. (2014)
"""

from __future__ import annotations
from dataclasses import dataclass

from backend.domain.assessment.value_objects import ArtistryScore


@dataclass(frozen=True)
class ArtistryFeatures:
    """艺术表现特征输入 (不可变)"""
    vibrato_quality: float = 0.0     # 0-100
    vibrato_count: int = 0
    dynamic_range: float = 0.0       # dB
    crescendo_quality: float = 0.0   # 0-100
    phrase_coherence: float = 0.0    # 0-100
    is_artistic_fluctuation: bool = False
    long_note_count: int = 0
    pitch_cv: float = 0.0            # coefficient of variation


class ArtistryScorer:
    """艺术表现评分器 — 纯计算, 零副作用"""

    def calculate(self, features: ArtistryFeatures) -> ArtistryScore:
        vibrato = self._calc_vibrato(features.vibrato_quality, features.vibrato_count)
        dynamic = self._calc_dynamic(features.dynamic_range, features.crescendo_quality)
        phrase = self._calc_phrase(
            features.phrase_coherence,
            features.is_artistic_fluctuation,
            features.long_note_count,
        )
        pitch_var = self._calc_pitch_variation(features.pitch_cv)

        score = vibrato * 0.30 + dynamic * 0.30 + phrase * 0.25 + pitch_var * 0.15
        score = max(0.0, min(100.0, score))

        diagnosis: list[str] = []
        if vibrato > 70:
            diagnosis.append("颤音技巧运用出色")
        if dynamic > 70:
            diagnosis.append("动态对比丰富")
        if phrase > 70:
            diagnosis.append("乐句处理细腻")

        return ArtistryScore(
            raw_score=round(score, 1),
            vibrato_quality=round(vibrato, 1),
            dynamic_control=round(dynamic, 1),
            phrase_expression=round(phrase, 1),
            pitch_variation=round(pitch_var, 1),
            diagnosis=tuple(diagnosis),
        )

    @staticmethod
    def _calc_vibrato(quality: float, count: int) -> float:
        """颤音表现力 = vibrato_quality * 0.80 + count_bonus"""
        if count == 0:
            return 0.0
        quality_score = quality * 0.80
        count_bonus = min(20.0, count * 2.0)
        return min(100.0, quality_score + count_bonus)

    @staticmethod
    def _calc_dynamic(dynamic_range: float, crescendo_quality: float) -> float:
        """动态控制 = dynamic_range映射 + crescendo_quality映射"""
        score = min(60.0, dynamic_range * 2.0)
        score += crescendo_quality * 0.40
        return min(100.0, score)

    @staticmethod
    def _calc_phrase(
        coherence: float,
        is_artistic: bool,
        long_note_count: int,
    ) -> float:
        """乐句处理 = coherence * 0.70 + artistic_bonus + long_note_bonus"""
        score = coherence * 0.70
        if is_artistic:
            score += 30.0
        if long_note_count > 0:
            score += min(10.0, long_note_count * 2.0)
        return min(100.0, score)

    @staticmethod
    def _calc_pitch_variation(pitch_cv: float) -> float:
        """音高变化表现力 — dual折线映射: 低区上升, 中区平台, 高区下降"""
        if pitch_cv <= 0:
            return 0.0
        if pitch_cv < 0.03:
            return pitch_cv / 0.03 * 20.0               # 0→0, 0.03→20
        elif pitch_cv < 0.10:
            return 20.0 + (pitch_cv - 0.03) / 0.07 * 50  # 0.03→20, 0.10→70
        elif pitch_cv < 0.20:
            return 70.0 + (pitch_cv - 0.10) / 0.10 * 20  # 0.10→70, 0.20→90
        else:
            return max(30.0, 90.0 - (pitch_cv - 0.20) * 80)
