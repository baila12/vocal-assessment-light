"""
音色调整器 v7.0 — NEW ⚠️ 启发式代理指标

ADR-2: 音色评估使用谱质心偏离、MFCC聚类纯度、鼻音指数等代理指标。
不对称设计: 最多 +3, 最多 -5 (扣分比加分重)。
低置信度 (MFCC 聚类纯度 < 0.6) 自动归零。
"""

from __future__ import annotations
from dataclasses import dataclass

from backend.domain.assessment.value_objects import TimbreAdjustment


@dataclass
class TimbreFeatures:
    """音色特征输入 — ⚠️ 主观感知量的代理指标"""
    spectral_centroid_deviation: float = 0.0
    mfcc_cluster_distance: float = 0.0
    mfcc_cluster_purity: float = 1.0     # 0-1 confidence
    harmonic_richness: float = 0.5        # 0-1
    nasality_index: float = 0.0           # 0-1


class TimbreAdjuster:
    """音色调整器 — ⚠️ HEURISTIC: 主观感知代理指标"""

    def calculate(self, features: TimbreFeatures) -> TimbreAdjustment:
        # HEURISTIC: Subjective perceptual proxy from microphone audio

        # 1. Brightness
        brightness = self._calc_brightness(features.spectral_centroid_deviation)

        # 2. Warmth
        warmth = self._calc_warmth(
            features.harmonic_richness, features.mfcc_cluster_distance
        )

        # 3. Nasality
        nasality_q = self._calc_nasality(features.nasality_index)

        # Timbre quality score
        quality = brightness * 0.30 + warmth * 0.30 + nasality_q * 0.40

        # Asymmetric adjustment mapping
        if quality >= 80:
            adjustment = 3.0
        elif quality >= 60:
            adjustment = 1.0
        elif quality >= 40:
            adjustment = 0.0
        elif quality >= 20:
            adjustment = -2.0
        elif quality >= 10:
            adjustment = -3.0
        else:
            adjustment = -5.0

        # Low confidence gate
        confidence = features.mfcc_cluster_purity
        if confidence < 0.6:
            adjustment = 0.0
            diagnosis = "音色置信度不足(归零)"
        else:
            diagnosis_map = {
                3.0: "音色纯净",
                1.0: "音色良好",
                0.0: "音色普通",
                -2.0: "略有音色问题",
                -3.0: "音色偏差较大",
                -5.0: "音色存在问题",
            }
            diagnosis = diagnosis_map.get(adjustment, "")

        return TimbreAdjustment(
            adjustment=adjustment,
            brightness_score=round(brightness, 1),
            warmth_score=round(warmth, 1),
            nasality_score=round(nasality_q, 1),
            confidence=confidence,
            is_heuristic=True,
            diagnosis=diagnosis,
        )

    @staticmethod
    def _calc_brightness(deviation: float) -> float:
        # HEURISTIC: Subjective perceptual proxy from microphone audio
        if deviation < 0.10:
            return 100.0
        elif deviation < 0.25:
            return 70.0 + (0.25 - deviation) / 0.15 * 30
        elif deviation < 0.50:
            return 40.0 + (0.50 - deviation) / 0.25 * 30
        else:
            return max(5.0, 10.0 - (deviation - 0.50) * 5)

    @staticmethod
    def _calc_warmth(richness: float, cluster_distance: float) -> float:
        # HEURISTIC: Subjective perceptual proxy from microphone audio
        if richness > 0.7 and cluster_distance < 0.15:
            return 100.0
        elif richness > 0.4 or cluster_distance < 0.3:
            return 60.0
        else:
            return 20.0

    @staticmethod
    def _calc_nasality(index: float) -> float:
        # HEURISTIC: Subjective perceptual proxy from microphone audio
        if index < 0.10:
            return 100.0
        elif index < 0.30:
            return 60.0 + (0.30 - index) / 0.20 * 40
        elif index < 0.50:
            return 30.0 + (0.50 - index) / 0.20 * 30
        else:
            return max(0.0, 5.0 - (index - 0.50) * 5)
