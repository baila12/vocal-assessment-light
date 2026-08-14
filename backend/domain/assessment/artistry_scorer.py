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
    is_artistic_fluctuation: bool = False   # deprecated — 使用 artistic_fluctuation_score
    artistic_fluctuation_score: float = 0.0 # v7.6: 连续化 0-100
    long_note_count: int = 0
    pitch_cv: float = 0.0            # coefficient of variation
    rubato_score: float = 0.0        # v7.6: 表现性节奏变化 0-100


class ArtistryScorer:
    """艺术表现评分器 — 纯计算, 零副作用"""

    def calculate(self, features: ArtistryFeatures) -> ArtistryScore:
        vibrato = self._calc_vibrato(
            features.vibrato_quality, features.vibrato_count,
            features.pitch_cv,           # v7.4: fallback
            features.dynamic_range,      # v7.4: fallback
        )
        dynamic = self._calc_dynamic(features.dynamic_range, features.crescendo_quality)
        phrase = self._calc_phrase(
            features.phrase_coherence,
            features.is_artistic_fluctuation,
            features.long_note_count,
            features.artistic_fluctuation_score,  # v7.6: 连续化
            features.rubato_score,                # v7.6: 表现性节奏变化
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
    def _calc_vibrato(
        quality: float, count: int,
        pitch_cv: float = 0.0,          # v7.4: fallback 特征
        dynamic_range: float = 15.0,    # v7.4: fallback 特征
    ) -> float:
        """颤音表现力 = vibrato_quality + 无颤音时的 fallback

        文献: TECH_RESEARCH §2.6 — 无颤音歌手可能其他表现力强。
        流行/R&B/说唱唱法不以颤音为主要表现手段。
        """
        if count > 0:
            # 有颤音: 正常评分
            quality_score = quality * 0.80
            count_bonus = min(20.0, count * 2.0)
            return min(100.0, quality_score + count_bonus)

        # === 无颤音 fallback: 用音高变化 + 动态范围替代 ===
        # 原理: 表现力也可以通过音高多样性和动态对比体现
        # 上限 80 分 — 没有颤音的歌手不会得到颤音维度的满分

        # 音高变化 (pitch_cv):
        if pitch_cv <= 0:
            pitch_score = 0.0
        elif pitch_cv < 0.03:
            pitch_score = pitch_cv / 0.03 * 20.0
        elif pitch_cv < 0.10:
            pitch_score = 20.0 + (pitch_cv - 0.03) / 0.07 * 30.0
        elif pitch_cv < 0.20:
            pitch_score = 50.0 + (pitch_cv - 0.10) / 0.10 * 10.0
        else:
            pitch_score = min(60.0, 60.0 - (pitch_cv - 0.20) * 50.0)

        # 动态范围: 0→0, 15→20, 30→40
        dynamic_score = min(40.0, dynamic_range * 1.33)

        return min(80.0, pitch_score + dynamic_score)

    @staticmethod
    def _calc_dynamic(dynamic_range: float, crescendo_quality: float) -> float:
        """动态控制 = dynamic_range映射 + crescendo_quality映射

        v7.17 B4: 斜率 2.0→2.6, crescendo 权重 0.40→0.45, 上限 60→70 —
        实测高分真实音频 dynamic_range 20-25dB / crescendo 57-61, 旧曲线仅得 ~60-65
        (典型歌声动态 18-25dB, 文献 Canazza 2014)。
        """
        score = min(70.0, dynamic_range * 2.6)
        score += crescendo_quality * 0.45
        return min(100.0, score)

    @staticmethod
    def _calc_phrase(
        coherence: float,
        is_artistic: bool,
        long_note_count: int,
        artistic_fluctuation_score: float = 0.0,  # v7.6: 连续化
        rubato_score: float = 0.0,                # v7.6: 表现性节奏变化
    ) -> float:
        """乐句处理 = coherence*0.55 + fluctuation*0.25 + rubato*0.10 + long_note

        v7.6: 用连续 float 替代布尔 +30, 新增 rubato 维度 (0-10 分贡献)。
        """
        score = coherence * 0.55
        # v7.6: 优先使用连续分数 (0→0, 100→25), fallback 到旧布尔
        # v7.17 B4: 波动权重 0.25→0.30 (实测高分 afs 38-53, 旧曲线贡献偏低)
        if artistic_fluctuation_score > 0:
            score += artistic_fluctuation_score * 0.30
        elif is_artistic:
            score += 25.0  # backward compat
        # v7.6: rubato 贡献 (最多 10 分), 仅在检测到 onset 变化时激活
        if rubato_score > 0:
            score += min(10.0, rubato_score * 0.10)
        if long_note_count > 0:
            score += min(10.0, long_note_count * 2.0)
        return min(100.0, score)

    @staticmethod
    def _calc_pitch_variation(pitch_cv: float) -> float:
        """音高变化表现力 — dual折线映射: 低区上升, 中区平台, 高区下降

        v7.17 B4: 高区斜率 80→55, 顶 90→92 — 实测高分音频 pitch_cv ~0.5 (真实演唱
        自然音高波动), 旧曲线 0.5 仅得 66, 新曲线得 ~75 (Sundberg 1987 表现力)。
        """
        if pitch_cv <= 0:
            return 0.0
        if pitch_cv < 0.03:
            return pitch_cv / 0.03 * 20.0               # 0→0, 0.03→20
        elif pitch_cv < 0.10:
            return 20.0 + (pitch_cv - 0.03) / 0.07 * 50  # 0.03→20, 0.10→70
        elif pitch_cv < 0.20:
            return 70.0 + (pitch_cv - 0.10) / 0.10 * 22  # 0.10→70, 0.20→92
        else:
            return max(30.0, 92.0 - (pitch_cv - 0.20) * 55)
