"""
音色调整器 v7.0 — NEW ⚠️ 启发式代理指标

ADR-2: 音色评估使用谱质心偏离、MFCC聚类纯度、鼻音指数等代理指标。
不对称设计: 最多 +3, 最多 -5 (扣分比加分重)。
低置信度 (MFCC 聚类纯度 < 0.6) 自动归零。

v7.3: audiofeat 增强 — 直接谱测量 (centroid/roughness/nasality/inharmonicity)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import TYPE_CHECKING

from backend.domain.assessment.value_objects import TimbreAdjustment

if TYPE_CHECKING:
    from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures


@dataclass(frozen=True)
class TimbreFeatures:
    """音色特征输入 — ⚠️ 主观感知量的代理指标 (不可变)"""
    spectral_centroid_deviation: float = 0.0
    mfcc_cluster_distance: float = 0.0
    mfcc_cluster_purity: float = 1.0     # 0-1 confidence
    harmonic_richness: float = 0.5        # 0-1
    nasality_index: float = 0.0           # 0-1


class TimbreAdjuster:
    """音色调整器 — ⚠️ HEURISTIC: 主观感知代理指标

    v7.3: 可选 audiofeat 增强 — 用直接谱测量增强音色评估:
      - spectral_centroid_mean → 直接亮度 (替换启发式)
      - spectral_roughness → 新增粗糙度维度
      - nasality → 直接鼻音测量
      - inharmonicity → 不和谐度惩罚
      - spectral_flatness → 音色复杂度
      - harmonic_richness → 谐波丰富度 (增强已有)
    """

    # ---- audiofeat 参考值 (v7.3) ----
    CENTROID_BRIGHT = 2000.0     # > 2000 Hz = 明亮
    CENTROID_WARM = 800.0        # < 800 Hz = 温暖
    ROUGHNESS_HIGH = 0.5         # > 0.5 = 明显粗糙
    NASALITY_HIGH = 0.5          # > 0.5 = 明显鼻音
    INHARMONICITY_HIGH = 0.3     # > 0.3 = 不和谐
    FLATNESS_HIGH = 0.6          # > 0.6 = 噪声化

    def calculate(
        self,
        features: TimbreFeatures,
        audiofeat: 'AudiofeatFeatures | None' = None,
    ) -> TimbreAdjustment:
        # v7.3: audiofeat 增强路径
        if audiofeat is not None and self._has_audiofeat_data(audiofeat):
            return self._calculate_enhanced(features, audiofeat)

        # 原有启发式路径
        return self._calculate_heuristic(features)

    # ================================================================
    # v7.3: audiofeat 增强路径
    # ================================================================

    @staticmethod
    def _has_audiofeat_data(af: 'AudiofeatFeatures') -> bool:
        """检查 audiofeat 是否有有效数据 (非全默认)"""
        return (
            af.spectral_centroid_mean > 0
            or af.harmonic_richness > 0
            or af.nasality > 0
            or af.spectral_roughness > 0
        )

    def _calculate_enhanced(
        self,
        features: TimbreFeatures,
        af: 'AudiofeatFeatures',
    ) -> TimbreAdjustment:
        """v7.3: audiofeat 增强 — 直接谱测量 + 启发式回退"""
        # 1. 亮度: audiofeat centroid 直接测量
        brightness = self._calc_enhanced_brightness(af.spectral_centroid_mean)

        # 2. 温暖度: harmonic_richness + centroid 综合
        warmth = self._calc_enhanced_warmth(
            af.harmonic_richness, af.spectral_centroid_mean,
            af.spectral_flatness_mean,
        )

        # 3. 鼻音: audiofeat 直接测量
        nasality_q = self._calc_enhanced_nasality(af.nasality)

        # 4. 粗糙度: audiofeat roughness + 不和谐度
        roughness_q = self._calc_enhanced_roughness(
            af.spectral_roughness, af.inharmonicity,
        )

        # 加权合成: brightness(25%) + warmth(25%) + nasality(25%) + roughness(25%)
        quality = (
            brightness * 0.25
            + warmth * 0.25
            + nasality_q * 0.25
            + roughness_q * 0.25
        )

        # 不对称调整 (与启发式路径一致)
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

        # 使用已有 mfcc_cluster_purity 作为置信度
        confidence = features.mfcc_cluster_purity
        if confidence < 0.6:
            adjustment = 0.0

        return TimbreAdjustment(
            adjustment=adjustment,
            brightness_score=round(brightness, 1),
            warmth_score=round(warmth, 1),
            nasality_score=round(nasality_q, 1),
            confidence=confidence,
            is_heuristic=True,
            diagnosis="audiofeat增强",
        )

    @staticmethod
    def _calc_enhanced_brightness(centroid: float) -> float:
        """audiofeat centroid → brightness (0-100)"""
        if centroid <= 0:
            return 50.0
        if centroid >= TimbreAdjuster.CENTROID_BRIGHT:
            return min(100.0, 80.0 + (centroid - 2000) / 1000 * 20)
        elif centroid <= TimbreAdjuster.CENTROID_WARM:
            return max(20.0, 40.0 - (800 - centroid) / 800 * 20)
        else:
            # 800-2000 Hz: linear 40→80
            return 40.0 + (centroid - 800) / 1200 * 40

    @staticmethod
    def _calc_enhanced_warmth(
        richness: float,
        centroid: float,
        flatness: float,
    ) -> float:
        """audiofeat richness + centroid + flatness → warmth (0-100)"""
        score = 50.0
        if richness > 0.7:
            score += 30.0
        elif richness > 0.4:
            score += 10.0
        if centroid > 0 and centroid < TimbreAdjuster.CENTROID_WARM:
            score += 15.0
        if flatness > TimbreAdjuster.FLATNESS_HIGH:
            score -= 20.0  # 过于平坦 = 噪声化, 不温暖
        return max(0.0, min(100.0, score))

    @staticmethod
    def _calc_enhanced_nasality(nasality: float) -> float:
        """audiofeat nasality → quality (0-100, 高=好=非鼻音)"""
        if nasality <= 0:
            return 80.0  # no data, assume good
        if nasality < 0.10:
            return 100.0
        elif nasality < 0.30:
            return 60.0 + (0.30 - nasality) / 0.20 * 40
        elif nasality < 0.50:
            return 30.0 + (0.50 - nasality) / 0.20 * 30
        else:
            return max(0.0, 5.0 - (nasality - 0.50) * 5)

    @staticmethod
    def _calc_enhanced_roughness(roughness: float, inharmonicity: float) -> float:
        """audiofeat roughness + inharmonicity → quality (0-100, 高=好=不粗糙)"""
        score = 100.0
        if roughness > TimbreAdjuster.ROUGHNESS_HIGH:
            penalty = min(60.0, (roughness - 0.5) * 120)
            score -= penalty
        if inharmonicity > TimbreAdjuster.INHARMONICITY_HIGH:
            penalty = min(40.0, (inharmonicity - 0.3) * 150)
            score -= penalty
        return max(0.0, min(100.0, score))

    # ================================================================
    # 原有启发式路径 (v7.0)
    # ================================================================

    def _calculate_heuristic(self, features: TimbreFeatures) -> TimbreAdjustment:
        """原有启发式音色评估"""
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
