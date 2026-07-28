"""TimbreAdjuster TDD — 6 tests, NEW heuristic timbre adjustment"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest
from backend.domain.assessment.timbre_adjuster import TimbreAdjuster, TimbreFeatures


def make_features(**kwargs) -> TimbreFeatures:
    defaults = {
        "spectral_centroid_deviation": 0.05,
        "mfcc_cluster_distance": 0.10,
        "mfcc_cluster_purity": 0.90,
        "harmonic_richness": 0.80,
        "nasality_index": 0.05,
    }
    defaults.update(kwargs)
    return TimbreFeatures(**defaults)


class TestTimbreAdjuster:
    def setup_method(self):
        self.adjuster = TimbreAdjuster()

    def test_pure_timbre_plus_3(self):
        f = make_features()  # all excellent
        result = self.adjuster.calculate(f)
        assert result.adjustment == 3
        assert result.is_heuristic is True

    def test_average_timbre_zero(self):
        f = make_features(
            spectral_centroid_deviation=0.30,
            mfcc_cluster_distance=0.30,
            harmonic_richness=0.40,
            nasality_index=0.20,
        )
        result = self.adjuster.calculate(f)
        assert result.adjustment == 0

    def test_nasal_minus_2(self):
        f = make_features(
            spectral_centroid_deviation=0.30,
            harmonic_richness=0.40,
            nasality_index=0.55,
        )
        result = self.adjuster.calculate(f)
        assert result.adjustment == -2

    def test_severe_hoarseness_minus_5(self):
        f = make_features(
            spectral_centroid_deviation=1.2,
            mfcc_cluster_distance=0.8,
            harmonic_richness=0.02,
            nasality_index=0.80,
        )
        result = self.adjuster.calculate(f)
        assert result.adjustment == -5

    def test_low_confidence_zero(self):
        f = make_features(mfcc_cluster_purity=0.3)  # below 0.6 threshold
        result = self.adjuster.calculate(f)
        assert result.adjustment == 0
        assert result.confidence == 0.3

    def test_apply_clamp(self):
        # Total=98, adjustment=+3 → 100 (not 101)
        f_pure = make_features()
        adj_pure = self.adjuster.calculate(f_pure)
        assert adj_pure.apply(98.0) == 100.0

        # Total=3, adjustment=-5 → 0 (not -2)
        f_bad = make_features(
            spectral_centroid_deviation=0.70, mfcc_cluster_distance=0.60,
            harmonic_richness=0.10, nasality_index=0.60,
        )
        adj_bad = self.adjuster.calculate(f_bad)
        assert adj_bad.apply(3.0) == 0.0


# ================================================================
# v7.3: TimbreAdjuster + audiofeat 增强测试
# ================================================================

def _make_audiofeat(**kwargs):
    """构造 AudiofeatFeatures 测试数据"""
    from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures
    return AudiofeatFeatures(**kwargs)


class TestTimbreAdjusterAudiofeat:
    """TimbreAdjuster audiofeat 增强路径测试 — v7.3"""

    def setup_method(self):
        self.adjuster = TimbreAdjuster()

    # ---- 向后兼容 ----

    def test_audiofeat_none_falls_back_to_heuristic(self):
        """audiofeat=None → 使用原有启发式路径"""
        f = make_features()
        result = self.adjuster.calculate(f, audiofeat=None)
        assert result.adjustment == 3  # pure timbre → +3
        assert result.is_heuristic is True

    def test_audiofeat_all_defaults_no_effect(self):
        """全零 audiofeat → 回退到启发式"""
        f = make_features()
        af = _make_audiofeat()
        result = self.adjuster.calculate(f, audiofeat=af)
        assert result.adjustment == 3  # falls back to heuristic path

    # ---- 增强亮度 (spectral_centroid) ----

    def test_audiofeat_enhanced_brightness_high(self):
        """高 centroid (>2000Hz) → 明亮音色"""
        f = make_features()
        af = _make_audiofeat(spectral_centroid_mean=2500.0, harmonic_richness=0.8)
        result = self.adjuster.calculate(f, audiofeat=af)
        assert result.brightness_score > 70

    def test_audiofeat_enhanced_warmth_low_centroid(self):
        """低 centroid (<800Hz) + 丰富谐波 → 温暖音色"""
        f = make_features()
        af = _make_audiofeat(spectral_centroid_mean=600.0, harmonic_richness=0.85)
        result = self.adjuster.calculate(f, audiofeat=af)
        # 温暖度应较高
        assert result.warmth_score > 60

    # ---- 粗糙度 ----

    def test_audiofeat_roughness_high_penalizes(self):
        """高粗糙度 → 扣分"""
        f = make_features()
        af = _make_audiofeat(spectral_roughness=0.7, harmonic_richness=0.3)
        result = self.adjuster.calculate(f, audiofeat=af)
        result_no_af = self.adjuster.calculate(f)
        assert result.adjustment < result_no_af.adjustment

    # ---- 鼻音 ----

    def test_audiofeat_nasality_direct_penalty(self):
        """audiofeat 高鼻音 + 综合偏差 → 负调整"""
        f = make_features()
        af = _make_audiofeat(
            nasality=0.8, harmonic_richness=0.1,
            spectral_roughness=0.7, spectral_centroid_mean=500.0,
            inharmonicity=0.4, spectral_flatness_mean=0.7,
        )
        result = self.adjuster.calculate(f, audiofeat=af)
        assert result.adjustment == -2
        assert result.nasality_score < 20  # 高鼻音分低

    # ---- 不和谐度 ----

    def test_audiofeat_inharmonicity_penalty(self):
        """高不和谐度 → 扣分"""
        f = make_features()
        af = _make_audiofeat(inharmonicity=0.4, harmonic_richness=0.3)
        result = self.adjuster.calculate(f, audiofeat=af)
        result_no_af = self.adjuster.calculate(f)
        assert result.adjustment < result_no_af.adjustment

    # ---- 增强路径完整性 ----

    def test_audiofeat_enhanced_path_in_range(self):
        """增强路径 adjustments 在 [-5, +3] 内"""
        import random
        for _ in range(20):
            f = make_features()
            af = _make_audiofeat(
                spectral_centroid_mean=random.uniform(200, 4000),
                harmonic_richness=random.uniform(0.0, 1.0),
                spectral_roughness=random.uniform(0.0, 0.8),
                nasality=random.uniform(0.0, 0.9),
                inharmonicity=random.uniform(0.0, 0.5),
                spectral_flatness_mean=random.uniform(0.0, 0.8),
            )
            result = self.adjuster.calculate(f, audiofeat=af)
            assert -5 <= result.adjustment <= 3

    def test_audiofeat_enhanced_is_heuristic(self):
        """增强路径仍标记为 heuristic (非直接生理测量)"""
        f = make_features()
        af = _make_audiofeat(spectral_centroid_mean=1500.0, harmonic_richness=0.6)
        result = self.adjuster.calculate(f, audiofeat=af)
        assert result.is_heuristic is True
