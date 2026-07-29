"""
音色调整器 v7.5 — NEW ⚠️ 启发式代理指标

ADR-2: 音色评估使用谱质心偏离、MFCC聚类纯度、鼻音指数等代理指标。
不对称设计: 最多 +3, 最多 -5 (扣分比加分重)。
低置信度 (MFCC 聚类纯度 < 0.6) 自动归零。

v7.3: audiofeat 增强 — 直接谱测量 (centroid/roughness/nasality/inharmonicity)
v7.5: P1-2b 音色八维剖面 — hardness/depth/sharpness/booming (需 enable_audiofeat=True)
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
    mfcc_cluster_purity: float = 1.0     # 0-1 confidence (from CPP/6 or harmonic_stability)
    harmonic_richness: float = 0.5        # 0-1
    nasality_index: float = 0.0           # 0-1
    harmonic_stability: float = 50.0      # v7.4: 0-100, alternative confidence source


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
        """v7.5: audiofeat 八维音色剖面 — 直接谱测量 + 启发式回退

        v7.3 四维: brightness(25%) + warmth(25%) + nasality(25%) + roughness(25%)
        v7.5 八维: 各 12.5% 等权 — brightness + warmth + nasality + roughness
                    + hardness + depth + sharpness + booming

        设计注记 (ADR):
        - brightness 和 sharpness 共享 spectral_centroid_mean 输入，
          但评分函数不同: brightness 为单调(亮=好), sharpness 为甜点曲线(适中=好)。
          共享输入使 centroid 实际影响约 25% (而非名义 12.5%)，
          这是有意为之: centroid 是 timbral_models 中验证最充分的维度 (r=0.967)。
        - hardness 和 sharpness 使用甜点曲线 (倒U形), 避免极端值获得意外高分。
        """
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

        # 5-8. v7.5 P1-2b: 新增四维
        hardness = self._calc_hardness(af.spectral_crest)
        depth = self._calc_depth(af.hammarberg_index, af.spectral_slope)
        sharpness = self._calc_sharpness(af.spectral_centroid_mean)
        booming = self._calc_booming(af.hammarberg_index, af.harmonic_richness)

        # 八维等权融合 (各 12.5%)
        quality = (
            brightness * 0.125
            + warmth * 0.125
            + nasality_q * 0.125
            + roughness_q * 0.125
            + hardness * 0.125
            + depth * 0.125
            + sharpness * 0.125
            + booming * 0.125
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

        # v7.4: 双源置信度 — mfcc_cluster_purity + harmonic_stability fallback
        confidence = max(
            features.mfcc_cluster_purity,
            features.harmonic_stability / 100.0,
        )
        if confidence < 0.6:
            adjustment = 0.0

        return TimbreAdjustment(
            adjustment=adjustment,
            brightness_score=round(brightness, 1),
            warmth_score=round(warmth, 1),
            nasality_score=round(nasality_q, 1),
            confidence=confidence,
            is_heuristic=True,
            diagnosis="audiofeat八维增强",
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
    # v7.5 P1-2b: 音色八维剖面新增维度
    # ================================================================

    @staticmethod
    def _calc_hardness(spectral_crest: float) -> float:
        """Hardness (2-5kHz 能量集中度) → 甜点曲线 (0-100)

        文献: timbral_models — 2-5kHz 能量比反映音色"硬度"
        - 典型歌声 spectral_crest: 6-14, 最佳区间 7-11
        - 过硬 > 14: 刺耳, 过软 < 4: 虚弱
        - 中性值 50 为默认
        """
        if spectral_crest <= 0:
            return 50.0  # 无数据 → 中性

        # 甜点曲线: 最佳在 7-11 之间
        if 7.0 <= spectral_crest <= 11.0:
            return 85.0 + (spectral_crest - 7.0) / 4.0 * 15.0  # 7→85, 11→100
        elif 4.0 <= spectral_crest < 7.0:
            return 40.0 + (spectral_crest - 4.0) / 3.0 * 45.0   # 4→40, 7→85
        elif 11.0 < spectral_crest <= 16.0:
            return 40.0 + (16.0 - spectral_crest) / 5.0 * 45.0  # 16→40, 11→85
        elif spectral_crest > 16.0:
            return max(5.0, 40.0 - (spectral_crest - 16.0) * 3.0)  # >16 → falling
        else:  # < 4.0
            return max(5.0, spectral_crest / 4.0 * 40.0)         # 0→0, 4→40

    @staticmethod
    def _calc_depth(
        hammarberg_index: float,
        spectral_slope: float,
    ) -> float:
        """Depth (30-200Hz 低频突出度) → hammarberg_index + slope (0-100)

        文献: timbral_models — 低频能量突出度反映音色"深度/厚度"
        - Hammarberg Index (0-2kHz / 2-5kHz): 高 = 低频能量多 = 深沉
          典型歌声: 0.3-2.0
        - Spectral Slope: 平缓 (> -6 dB/oct) = 低频相对强 = 深沉
        """
        if hammarberg_index <= 0:
            return 50.0  # 无数据 → 中性

        # Hammarberg 主导 (70%): 低频/高频能量比
        if hammarberg_index >= 2.0:
            hi_score = 70.0
        elif hammarberg_index >= 1.2:
            hi_score = 40.0 + (hammarberg_index - 1.2) / 0.8 * 30.0  # 1.2→40, 2.0→70
        elif hammarberg_index >= 0.6:
            hi_score = 15.0 + (hammarberg_index - 0.6) / 0.6 * 25.0  # 0.6→15, 1.2→40
        elif hammarberg_index >= 0.3:
            hi_score = 5.0 + (hammarberg_index - 0.3) / 0.3 * 10.0   # 0.3→5, 0.6→15
        else:
            hi_score = max(0.0, hammarberg_index / 0.3 * 5.0)         # 0→0, 0.3→5

        # Spectral Slope 辅助 (30%): 更平缓的斜率 = 更多低频
        # 注: 真实歌声斜率为负 (-6~-18 dB/oct), 0.0 为 dataclass 默认值(无数据)
        if spectral_slope >= 0.0:
            slope_score = 15.0  # 默认值/无数据 → 中性, 不给 bonus
        elif spectral_slope >= -6.0:
            slope_score = 30.0
        elif spectral_slope >= -10.0:
            slope_score = 15.0 + (-6.0 - spectral_slope) / 4.0 * 15.0  # -10→15, -6→30
        elif spectral_slope >= -15.0:
            slope_score = 5.0 + (-10.0 - spectral_slope) / 5.0 * 10.0   # -15→5, -10→15
        else:
            slope_score = max(0.0, 5.0 + (spectral_slope + 15.0) * 0.5)  # <-15→≤5

        return hi_score + slope_score

    @staticmethod
    def _calc_sharpness(spectral_centroid: float) -> float:
        """Sharpness (高频能量集中度) → 甜点曲线 (0-100, 最佳=适中清晰度)

        文献: timbral_models — 最佳 centroid ~1500-2500Hz
        - 太尖锐 > 3500Hz: 刺耳 → 低分
        - 太沉闷 < 800Hz: 缺乏清晰度 → 低分
        - 最佳 1200-2800Hz: 清晰但不刺耳
        """
        if spectral_centroid <= 0:
            return 50.0  # 无数据 → 中性

        # 甜点曲线: 最佳 1200-2800 Hz
        if 1200.0 <= spectral_centroid <= 2800.0:
            # 最佳区间: 80-100, peak at midpoint 2000 Hz
            peak = (1200.0 + 2800.0) / 2.0  # 2000 Hz
            half_width = peak - 1200.0  # 800 Hz
            dist = abs(spectral_centroid - peak) / half_width  # 0 at peak, 1 at edges
            return 100.0 - dist * 20.0  # 100→80 in sweet spot
        elif 800.0 <= spectral_centroid < 1200.0:
            return 40.0 + (spectral_centroid - 800.0) / 400.0 * 40.0  # 800→40, 1200→80
        elif 2800.0 < spectral_centroid <= 4000.0:
            return 40.0 + (4000.0 - spectral_centroid) / 1200.0 * 40.0  # 4000→40, 2800→80
        elif spectral_centroid > 4000.0:
            return max(5.0, 40.0 - (spectral_centroid - 4000.0) / 200.0 * 5.0)  # >4000 → falling
        else:  # < 800
            return max(5.0, spectral_centroid / 800.0 * 40.0)  # 0→0, 800→40

    @staticmethod
    def _calc_booming(
        hammarberg_index: float,
        harmonic_richness: float,
    ) -> float:
        """Booming (低频共鸣 + 歌手共振峰) → 分段线性融合 (0-100)

        评分 = lf_score (60%: hammarberg 低频共鸣) + sf_score (40%: harmonic_richness 歌手共振峰)

        文献: timbral_models — 洪亮 = 强低频共鸣 + 突出歌手共振峰
        - 歌手共振峰 (2.5-3.5kHz) 增强 → harmonic_richness 高
        - 低频能量 (30-200Hz) 充足 → hammarberg_index 高
        """
        if hammarberg_index <= 0 and harmonic_richness <= 0:
            return 50.0  # 无数据 → 中性

        # Low frequency resonance (60%)
        if hammarberg_index >= 2.0:
            lf_score = 60.0
        elif hammarberg_index >= 1.2:
            lf_score = 35.0 + (hammarberg_index - 1.2) / 0.8 * 25.0
        elif hammarberg_index >= 0.6:
            lf_score = 15.0 + (hammarberg_index - 0.6) / 0.6 * 20.0
        elif hammarberg_index > 0:
            lf_score = hammarberg_index / 0.6 * 15.0
        else:
            lf_score = 30.0  # 无低频数据 → 中性分量

        # Singer's formant / harmonic richness (40%)
        if harmonic_richness >= 0.85:
            sf_score = 40.0
        elif harmonic_richness >= 0.6:
            sf_score = 20.0 + (harmonic_richness - 0.6) / 0.25 * 20.0
        elif harmonic_richness >= 0.3:
            sf_score = 10.0 + (harmonic_richness - 0.3) / 0.3 * 10.0
        elif harmonic_richness > 0:
            sf_score = harmonic_richness / 0.3 * 10.0
        else:
            sf_score = 20.0  # 无谐波数据 → 中性分量

        return lf_score + sf_score

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

        # v7.4: 双源置信度 — mfcc_cluster_purity 可能因旧 CPP 极低而不可靠
        confidence = max(
            features.mfcc_cluster_purity,
            features.harmonic_stability / 100.0,
        )
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
