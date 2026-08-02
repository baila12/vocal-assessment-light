"""
气息评分器 v7.0 — 移植 v6.3 四子维度连续线性映射

四大细分维度: 长音支撑(40%)、动态控制(25%)、气口设计(20%)、气声技巧(15%)

v7.3: audiofeat 增强 — CPPS/GNE/HNR_praat 用于精化气息评估
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.domain.assessment.value_objects import BreathScore

if TYPE_CHECKING:
    from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures


@dataclass(frozen=True)
class BreathFeatures:
    """气息特征输入 (不可变)"""
    professional_breath_score: float = 0.0
    long_note_support: float = 0.0
    dynamic_control: float = 0.0
    breath_design: float = 0.0
    breath_technique: float = 0.0
    rms_fluctuation: float = 0.0
    is_artistic_fluctuation: bool = False    # deprecated — 使用 artistic_fluctuation_score
    artistic_fluctuation_score: float = 0.0 # v7.6: 连续化 0-100
    controlled_breathiness: float = 0.0
    uncontrolled_leak: float = 0.0
    breath_breaks: int = 0
    long_note_count: int = 0
    soft_segment_count: int = 0
    soft_singing_quality: float = 0.0
    clean_breath_count: int = 0
    dynamic_range: float = 0.0
    phrase_coherence: float = 0.0       # v7.1.2: 子维度 (适配 artistry)
    crescendo_quality: float = 0.0      # v7.1.2: 子维度 (适配 artistry)
    long_note_decay: float = 0.0        # v7.1.2: 子维度 (适配 muscle rms_decay)
    pitch_stability_long: float = 0.0   # v7.1.2: 子维度 (适配 muscle formant_cluster)
    harmonic_stability: float = 50.0    # v7.1.3: 子维度 (适配 timbre harmonic_richness)
    is_clean_vocal: bool = False


class BreathScorer:
    """气息评分器 — 纯计算, 零副作用

    v7.3: 可选 audiofeat 参数增强评分精度:
      - GNE (Glottal-to-Noise Excitation): 区分可控气声 vs 不可控漏气
      - CPPS (Cepstral Peak Prominence Smoothed): 声门闭合质量
      - HNR_praat: 比 librosa HNR 更准确的谐波噪声比
    """

    # ---- audiofeat 阈值 (v7.3) ----
    GNE_LEAK_THRESHOLD = 0.4       # GNE < 0.4 = 声门激励不规律
    GNE_QUALITY_THRESHOLD = 0.8    # GNE > 0.8 = 优秀声门控制
    CPPS_QUALITY_THRESHOLD = 8.0   # CPPS > 8 dB = 清晰声门闭合
    CPPS_WEAK_THRESHOLD = 3.0      # CPPS < 3 dB = 声门闭合极弱
    HNR_LEAK_THRESHOLD = 5.0       # HNR < 5 dB = 严重漏气
    HNR_LOW_THRESHOLD = 10.0       # HNR < 10 dB = 漏气迹象

    LEAK_PENALTY = 8.0             # 不可控漏气最大扣分
    QUALITY_BONUS = 3.0            # 优秀声门控制最大加分

    def calculate(
        self,
        features: BreathFeatures,
        audiofeat: 'AudiofeatFeatures | None' = None,
    ) -> BreathScore:
        # 1. 主分: professional score 优先, 否则 fallback 到 fluctuation
        if features.professional_breath_score > 0:
            score = features.professional_breath_score
        else:
            score = self._score_from_fluctuation(features.rms_fluctuation)

        # 2. 长音加分
        if features.long_note_support > 80:
            score += 5.0
        elif features.long_note_support > 60:
            pass  # 良好无加分

        # 3. 弱唱加分
        if features.soft_singing_quality > 70:
            score += 5.0
        elif features.soft_singing_quality > 50:
            pass

        # 4. 气息断层惩罚
        if features.breath_breaks > 3:
            penalty = min(15.0, (features.breath_breaks - 3) * 3.0)
            score -= penalty

        # 5. v7.3: audiofeat 增强
        if audiofeat is not None:
            score = self._apply_audiofeat_enhancement(score, features, audiofeat)

        score = max(0.0, min(100.0, score))

        diagnosis: list[str] = []
        if features.is_artistic_fluctuation:
            diagnosis.append("检测到艺术化的强弱起伏处理")
        if features.uncontrolled_leak > 30:
            diagnosis.append("存在无效漏气")
        if features.breath_breaks > 3:
            diagnosis.append(f"存在{features.breath_breaks}处气息断层")

        return BreathScore(
            raw_score=round(score, 1),
            long_note_support=features.long_note_support,
            dynamic_control=features.dynamic_control,
            breath_design=features.breath_design,
            breath_technique=features.breath_technique,
            is_clean_vocal=features.is_clean_vocal,
            dynamic_range_db=features.dynamic_range,
            diagnosis=tuple(diagnosis),
        )

    def _apply_audiofeat_enhancement(
        self,
        score: float,
        features: BreathFeatures,
        af: 'AudiofeatFeatures',
    ) -> float:
        """v7.3: audiofeat 增强 — GNE + CPPS + HNR_praat 微调气息评分"""
        gne = af.gne_mean
        cpp = af.cpp_mean
        hnr = af.hnr_mean

        # 所有值为 0 (默认/不可用) → 无增强
        if gne == 0.0 and cpp == 0.0 and hnr == 0.0:
            return score

        # GNE: 区分可控气声 vs 不可控漏气
        if gne < self.GNE_LEAK_THRESHOLD and hnr > 0 and hnr < self.HNR_LOW_THRESHOLD:
            # 低 GNE + 低 HNR = 不可控漏气 (非艺术选择)
            leak_factor = (self.GNE_LEAK_THRESHOLD - gne) / self.GNE_LEAK_THRESHOLD
            penalty = self.LEAK_PENALTY * leak_factor
            score -= penalty
        elif gne > self.GNE_QUALITY_THRESHOLD and cpp > self.CPPS_QUALITY_THRESHOLD:
            # 高 GNE + 高 CPPS = 优秀声门控制
            quality_factor = min(
                (gne - self.GNE_QUALITY_THRESHOLD) / (1.0 - self.GNE_QUALITY_THRESHOLD),
                (cpp - self.CPPS_QUALITY_THRESHOLD) / 10.0,
            )
            score += self.QUALITY_BONUS * quality_factor

        # CPPS: 声门闭合质量
        if cpp > 0 and cpp < self.CPPS_WEAK_THRESHOLD:
            # CPPS 极低 = 声门闭合弱
            weakness = (self.CPPS_WEAK_THRESHOLD - cpp) / self.CPPS_WEAK_THRESHOLD
            score -= 3.0 * weakness

        # HNR_praat: 极低值验证漏气
        if hnr > 0 and hnr < self.HNR_LEAK_THRESHOLD:
            score -= 5.0

        return score

    @staticmethod
    def _score_from_fluctuation(fluctuation: float) -> float:
        """从 RMS 波动率计算基础分 (fallback)"""
        if fluctuation <= 0.20:
            return 100.0
        elif fluctuation <= 0.35:
            return 100.0 - (fluctuation - 0.20) * 250  # 100→62.5
        elif fluctuation <= 0.50:
            return 62.5 - (fluctuation - 0.35) * 250   # 62.5→25
        else:
            return max(10.0, 25.0 - (fluctuation - 0.50) * 100)
