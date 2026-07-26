"""
发声技术评分器 v7.0 — 重构: 咬字清晰度(50%) + 气声比(50%)

v6.3 旧版: HNR(40%) + CPP(30%) + technique(30%)
v7.0 新版: 拆分为两个独立子维度，每个基于可测量的声学特征
"""

from __future__ import annotations
from dataclasses import dataclass

from backend.domain.assessment.value_objects import TechniqueScore


@dataclass(frozen=True)
class TechniqueFeatures:
    """发声技术特征输入 (不可变)"""
    onset_density: float = 0.0       # onsets/second, 正常范围 1.5-5.0
    spectral_flux: float = 0.0       # 频谱变化率, 正常 < 3.0
    consonant_clarity: float = 0.0   # 辅音清晰度 0-100
    hnr_mean: float = 15.0           # 谐波噪声比 dB
    spectral_tilt: float = 0.0       # 频谱倾斜 (-10到+5, 负值=气声)
    hf_energy_ratio: float = 0.5     # >2kHz 能量占比
    cpp_mean: float = 1.0            # 声门闭合周期峰值
    vibrato_quality: float = 0.0     # v7.1.3: 颤音质量 0-100 (来自 TechniqueAnalyzer)
    vibrato_rate_avg: float = 5.0    # v7.1.3: 平均颤音速率 Hz (来自 TechniqueAnalyzer)


class TechniqueScorer:
    """发声技术评分器 — 纯计算, 零副作用"""

    def calculate(self, features: TechniqueFeatures) -> TechniqueScore:
        # 1. 咬字清晰度 (50%)
        articulation = self._calc_articulation(
            features.onset_density,
            features.spectral_flux,
            features.consonant_clarity,
        )

        # 2. 气声比 (50%)
        breath_voice = self._calc_breath_voice_ratio(
            features.hnr_mean,
            features.spectral_tilt,
            features.hf_energy_ratio,
        )

        # 加权合成
        score = articulation * 0.50 + breath_voice * 0.50
        score = max(0.0, min(100.0, score))

        diagnosis: list[str] = []
        if articulation < 40:
            diagnosis.append("咬字清晰度偏低")
        if breath_voice < 40:
            diagnosis.append("气声比失衡")

        return TechniqueScore(
            raw_score=round(score, 1),
            articulation_clarity=round(articulation, 1),
            breath_voice_ratio=round(breath_voice, 1),
            hnr_mean=features.hnr_mean,
            cpp_mean=features.cpp_mean,
            diagnosis=tuple(diagnosis),
        )

    @staticmethod
    def _calc_articulation(
        onset_density: float,
        spectral_flux: float,
        consonant_clarity: float,
    ) -> float:
        """咬字清晰度 = f(onset_density, spectral_flux, consonant_clarity)"""
        score = 0.0

        # consonant_clarity: 0→0, 100→50
        score += consonant_clarity * 0.50

        # onset_density: 1.5-5.0 → +25, outside → linear decay
        if 1.5 <= onset_density <= 5.0:
            score += 25.0
        elif onset_density > 0:
            dist = min(abs(onset_density - 1.5), abs(onset_density - 5.0))
            score += max(0.0, 25.0 - dist * 5.0)

        # spectral_flux 扣分: flux > 3.0 → penalty
        if spectral_flux > 3.0:
            penalty = min(25.0, (spectral_flux - 3.0) * 10.0)
            score -= penalty

        return max(0.0, min(100.0, score))

    @staticmethod
    def _calc_breath_voice_ratio(
        hnr_mean: float,
        spectral_tilt: float,
        hf_energy_ratio: float,
    ) -> float:
        """气声比 = f(HNR, spectral_tilt, hf_energy_ratio)"""
        score = 0.0

        # HNR: optimal 12-22 dB
        if 12 <= hnr_mean <= 22:
            score += 70.0
        elif hnr_mean < 5:
            score += 20.0  # very breathy
        elif hnr_mean > 30:
            score += 50.0  # unnaturally hard
        elif hnr_mean < 12:
            score += 20.0 + (hnr_mean - 5) / 7.0 * 50.0  # 5→20, 12→70
        else:  # 22-30
            score += 70.0 - (hnr_mean - 22) / 8.0 * 20.0  # 22→70, 30→50

        # Spectral tilt 惩罚: negative = breathy
        if spectral_tilt < -5:
            penalty = min(20.0, abs(spectral_tilt + 5) * 4.0)
            score -= penalty

        # HF energy ratio > 0.7 = breathy → penalty
        if hf_energy_ratio > 0.7:
            penalty = min(10.0, (hf_energy_ratio - 0.7) * 30.0)
            score -= penalty

        return max(0.0, min(100.0, score))
