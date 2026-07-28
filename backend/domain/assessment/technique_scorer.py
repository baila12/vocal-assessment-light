"""
发声技术评分器 v7.0 — 重构: 咬字清晰度(50%) + 气声比(50%)

v6.3 旧版: HNR(40%) + CPP(30%) + technique(30%)
v7.0 新版: 拆分为两个独立子维度，每个基于可测量的声学特征
v7.3: audiofeat 增强 — Jitter/Shimmer/Closed Quotient 用于精化技术评分
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.domain.assessment.value_objects import TechniqueScore

if TYPE_CHECKING:
    from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures


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
    """发声技术评分器 — 纯计算, 零副作用

    v7.3: 可选 audiofeat 参数增强评分精度:
      - Jitter (频率微扰): 咬字稳定性
      - Shimmer (幅度微扰): 振幅控制
      - Closed Quotient (声门闭合商): 发声效率
    """

    # ---- audiofeat 阈值 (v7.3) ----
    JITTER_EXCELLENT = 0.5     # < 0.5% = 极稳定
    JITTER_HIGH = 3.0           # > 3% = 不稳定 (病理)
    SHIMMER_EXCELLENT = 0.1     # < 0.1 dB = 极稳定
    SHIMMER_HIGH = 0.5          # > 0.5 dB = 不稳定
    CQ_OPTIMAL_LOW = 0.4        # 最优闭合商下限
    CQ_OPTIMAL_HIGH = 0.6       # 最优闭合商上限
    CQ_LOW = 0.2                # < 0.2 = 闭合不足

    JITTER_BONUS = 5.0          # 极稳定加分
    JITTER_PENALTY = 10.0       # 不稳定扣分
    SHIMMER_BONUS = 3.0         # 极稳定加分
    SHIMMER_PENALTY = 5.0       # 不稳定扣分
    CQ_BONUS = 3.0              # 高效发声加分
    CQ_PENALTY = 5.0            # 闭合不足扣分

    def calculate(
        self,
        features: TechniqueFeatures,
        audiofeat: 'AudiofeatFeatures | None' = None,
    ) -> TechniqueScore:
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

        # 3. v7.3: audiofeat 增强微调
        if audiofeat is not None:
            articulation, breath_voice = self._apply_audiofeat_enhancement(
                articulation, breath_voice, audiofeat,
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

    def _apply_audiofeat_enhancement(
        self,
        articulation: float,
        breath_voice: float,
        af: 'AudiofeatFeatures',
    ) -> tuple[float, float]:
        """v7.3: audiofeat 增强 — Jitter/Shimmer/CQ 微调子维度分数"""
        jitter = af.jitter_local
        shimmer = af.shimmer_db
        cq = af.closed_quotient

        # 所有值为 0 (默认/不可用) → 无增强
        if jitter == 0.0 and shimmer == 0.0 and cq == 0.0:
            return articulation, breath_voice

        # Jitter: 频率稳定性 → 影响咬字清晰度
        if jitter > 0 and jitter < self.JITTER_EXCELLENT:
            articulation = min(100.0, articulation + self.JITTER_BONUS)
        elif jitter > self.JITTER_HIGH:
            articulation = max(0.0, articulation - self.JITTER_PENALTY)

        # Shimmer: 振幅稳定性 → 影响气声比
        if shimmer > 0 and shimmer < self.SHIMMER_EXCELLENT:
            breath_voice = min(100.0, breath_voice + self.SHIMMER_BONUS)
        elif shimmer > self.SHIMMER_HIGH:
            breath_voice = max(0.0, breath_voice - self.SHIMMER_PENALTY)

        # Closed Quotient: 声门闭合效率 → 影响气声比
        if cq > 0:
            if self.CQ_OPTIMAL_LOW <= cq <= self.CQ_OPTIMAL_HIGH:
                breath_voice = min(100.0, breath_voice + self.CQ_BONUS)
            elif cq < self.CQ_LOW:
                breath_voice = max(0.0, breath_voice - self.CQ_PENALTY)

        return articulation, breath_voice

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
