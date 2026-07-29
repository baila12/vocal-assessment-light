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
        "harmonic_stability": 50.0,  # v7.4: 替代置信度源
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
        f = make_features(mfcc_cluster_purity=0.3, harmonic_stability=30.0)  # below 0.6 threshold
        result = self.adjuster.calculate(f)
        assert result.adjustment == 0
        assert result.confidence < 0.6  # v7.4: max(purity, harmonic/100)

    # ---- v7.4: Timbre gate fix (C2) ----

    def test_gate_fix_old_cpp_with_good_harmonic_stability(self):
        """旧 CPP≈0.018 无区分度但 harmonic_stability 高 → 音色生效 (不再归零)"""
        # 模拟旧 CPP 极低但 harmonic_stability 高的情况
        f = make_features(mfcc_cluster_purity=0.5, harmonic_stability=75.0)
        result = self.adjuster.calculate(f)
        # 有效置信度 = max(0.5, 75/100=0.75) = 0.75 >= 0.6 → 不归零
        assert result.confidence >= 0.6
        assert result.adjustment != 0  # 不应被门控归零

    def test_gate_fix_low_cpp_low_harmonic_still_zero(self):
        """CPP 低且 harmonic_stability 也低 → 仍然归零"""
        f = make_features(mfcc_cluster_purity=0.01, harmonic_stability=30.0)
        result = self.adjuster.calculate(f)
        # max(0.01, 30/100=0.30) = 0.30 < 0.6 → 归零
        assert result.adjustment == 0
        assert result.confidence < 0.6

    def test_gate_fix_uses_harmonic_stability(self):
        """高 harmonic_stability (>60) 可拯救低 CPP 音色"""
        f = make_features(mfcc_cluster_purity=0.003, harmonic_stability=80.0,
                          spectral_centroid_deviation=0.30, mfcc_cluster_distance=0.30,
                          harmonic_richness=0.40, nasality_index=0.20)
        result = self.adjuster.calculate(f)
        assert result.confidence == 0.8  # harmonic_stability/100
        assert result.adjustment == 0  # average timbre → 0

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


# ================================================================
# v7.5: TimbreAdjuster P1-2b — 音色八维剖面增强
# ================================================================

class TestTimbreEightDimension:
    """P1-2b: 音色八维剖面 — hardness/depth/sharpness/booming 新增"""

    def setup_method(self):
        self.adjuster = TimbreAdjuster()

    # ---- 新维度: Hardness (2-5kHz 能量比 → spectral_crest) ----

    def test_hardness_high_crest_is_bright_hard(self):
        """过高 spectral_crest (>14) → 偏离甜点 → 低分"""
        score = self.adjuster._calc_hardness(spectral_crest=14.0)
        # 14 在甜点右侧 (7-11 最佳), 应低于甜点区间分数
        assert 40 <= score <= 70  # 偏离甜点但未到极端

    def test_hardness_low_crest_is_soft(self):
        """低 spectral_crest (<4) → 偏离甜点 → 低分"""
        score = self.adjuster._calc_hardness(spectral_crest=2.0)
        assert score <= 40

    def test_hardness_sweet_spot_is_best(self):
        """spectral_crest 在 7-11 甜点区间 → 最高分"""
        score = self.adjuster._calc_hardness(spectral_crest=9.0)
        assert score >= 85  # 甜点区间应得高分

    def test_hardness_default_returns_neutral(self):
        """spectral_crest=0 → 返回中性 50"""
        score = self.adjuster._calc_hardness(spectral_crest=0.0)
        assert score == 50.0

    # ---- 新维度: Depth (30-200Hz 突出度 → hammarberg_index) ----

    def test_depth_high_low_freq_is_deep(self):
        """高 hammarberg_index (>1.5) → 深厚音色"""
        score = self.adjuster._calc_depth(
            hammarberg_index=2.0, spectral_slope=-3.0,
        )
        assert 70 <= score <= 100

    def test_depth_low_low_freq_is_thin(self):
        """低 hammarberg_index (<0.5) → 单薄音色"""
        score = self.adjuster._calc_depth(
            hammarberg_index=0.3, spectral_slope=-12.0,
        )
        assert score <= 40

    def test_depth_default_returns_neutral(self):
        """hammarberg_index=0 → 返回中性 50"""
        score = self.adjuster._calc_depth(
            hammarberg_index=0.0, spectral_slope=0.0,
        )
        assert score == 50.0

    def test_depth_default_slope_no_inflation(self):
        """spectral_slope=0.0 (dataclass 默认/无数据) + 低 hammarberg → 不膨胀"""
        score = self.adjuster._calc_depth(
            hammarberg_index=0.3, spectral_slope=0.0,
        )
        # slope=0.0 为无数据哨兵值, 应给中性分(15), 而非最大 bonus(30)
        # hammarberg=0.3 → hi_score=5, + slope=15 → total=20
        assert score <= 30, f"Default slope should not inflate depth, got {score}"

    # ---- 新维度: Sharpness (高频能量集中度 → centroid/4000) ----

    def test_sharpness_high_centroid_is_sharp(self):
        """过高 centroid (>3500Hz) → 偏离甜点 → 低分"""
        score = self.adjuster._calc_sharpness(spectral_centroid=3500.0)
        # 3500 超出甜点右侧 (1200-2800), 应偏低
        assert 30 <= score <= 60

    def test_sharpness_low_centroid_is_not_sharp(self):
        """低 centroid (<800Hz) → 偏离甜点 → 低分"""
        score = self.adjuster._calc_sharpness(spectral_centroid=600.0)
        assert score <= 40

    def test_sharpness_sweet_spot_is_best(self):
        """centroid 在 1200-2800Hz 甜点区间 → 最高分"""
        score = self.adjuster._calc_sharpness(spectral_centroid=2000.0)
        assert score >= 80

    def test_sharpness_default_returns_neutral(self):
        """centroid=0 → 返回中性 50"""
        score = self.adjuster._calc_sharpness(spectral_centroid=0.0)
        assert score == 50.0

    # ---- 新维度: Booming (低频共鸣 + 歌手共振峰) ----

    def test_booming_high_low_resonance_plus_richness(self):
        """高 hammarberg + 丰富谐波 → 洪亮音色"""
        score = self.adjuster._calc_booming(
            hammarberg_index=2.0, harmonic_richness=0.85,
        )
        assert 70 <= score <= 100

    def test_booming_low_resonance_flat_spectrum(self):
        """低 hammarberg + 弱谐波 → 不洪亮"""
        score = self.adjuster._calc_booming(
            hammarberg_index=0.3, harmonic_richness=0.2,
        )
        assert score <= 40

    def test_booming_default_returns_neutral(self):
        """全默认 → 返回中性 50"""
        score = self.adjuster._calc_booming(
            hammarberg_index=0.0, harmonic_richness=0.0,
        )
        assert score == 50.0

    # ---- 八维融合路径 ----

    def test_eight_dimension_path_activated_with_audiofeat(self):
        """audiofeat 提供有效数据 → 八维路径激活"""
        f = make_features()
        af = _make_audiofeat(
            spectral_centroid_mean=2000.0,
            harmonic_richness=0.7,
            spectral_roughness=0.15,
            nasality=0.05,
            spectral_crest=10.0,
            hammarberg_index=1.2,
            spectral_slope=-6.0,
            spectral_flatness_mean=0.3,
            inharmonicity=0.1,
        )
        result = self.adjuster.calculate(f, audiofeat=af)
        # 八维路径应产生有效调整
        assert -5 <= result.adjustment <= 3
        assert result.is_heuristic is True

    def test_eight_dimension_all_excellent_timbre(self):
        """八维全优 → 正向调整 ≥ +1 (quality ≥ 60)"""
        f = make_features(mfcc_cluster_purity=0.95, harmonic_stability=90.0)
        af = _make_audiofeat(
            spectral_centroid_mean=1800.0,  # balanced brightness
            harmonic_richness=0.9,           # rich harmonics
            spectral_roughness=0.02,         # smooth
            nasality=0.01,                   # not nasal
            spectral_crest=8.0,              # moderate hardness
            hammarberg_index=1.0,            # balanced depth
            spectral_slope=-5.0,             # normal slope
            spectral_flatness_mean=0.1,      # not flat
            inharmonicity=0.02,              # highly harmonic
        )
        result = self.adjuster.calculate(f, audiofeat=af)
        # 八维等权压缩了质量分数范围，≥60 即 +1 或更好
        assert result.adjustment >= 1, (
            f"Expected adjustment >= 1, got {result.adjustment}"
        )

    def test_eight_dimension_all_poor_timbre(self):
        """八维全差 → 负向调整 ≤ -2 (quality < 40)"""
        f = make_features(mfcc_cluster_purity=0.90, harmonic_stability=85.0)
        af = _make_audiofeat(
            spectral_centroid_mean=4000.0,   # extremely bright
            harmonic_richness=0.05,           # very poor harmonics
            spectral_roughness=0.9,           # extremely rough
            nasality=0.95,                    # very nasal
            spectral_crest=20.0,              # extremely hard
            hammarberg_index=0.1,             # very shallow
            spectral_slope=-20.0,             # very steep slope
            spectral_flatness_mean=0.95,      # completely flat
            inharmonicity=0.6,                # very inharmonic
        )
        result = self.adjuster.calculate(f, audiofeat=af)
        # 八维等权压缩了质量分数范围，全差场景应 ≤ -2
        assert result.adjustment <= -2, (
            f"Expected adjustment <= -2, got {result.adjustment}"
        )

    def test_eight_dimension_extreme_excellent_hits_plus_3(self):
        """极端优秀特征 (甜点区间) → +3"""
        f = make_features(mfcc_cluster_purity=0.98, harmonic_stability=95.0)
        af = _make_audiofeat(
            spectral_centroid_mean=1500.0,   # sweet spot for brightness & sharpness
            harmonic_richness=0.95,           # extremely rich
            spectral_roughness=0.0,           # perfectly smooth
            nasality=0.0,                     # no nasality
            spectral_crest=7.0,               # sweet spot hardness
            hammarberg_index=1.5,             # good depth
            spectral_slope=-4.0,              # gentle slope
            spectral_flatness_mean=0.05,      # not flat
            inharmonicity=0.0,                # perfectly harmonic
        )
        result = self.adjuster.calculate(f, audiofeat=af)
        # 理想特征组合应达到 +3
        assert result.adjustment == 3, (
            f"Expected +3 with ideal timbre, got {result.adjustment}"
        )

    def test_eight_dimension_extreme_poor_below_threshold(self):
        """极端差特征 (八维全面偏离甜点) → ≤ -3"""
        f = make_features(mfcc_cluster_purity=0.95, harmonic_stability=88.0)
        af = _make_audiofeat(
            spectral_centroid_mean=100.0,     # extremely dark (bad brightness, good warmth)
            harmonic_richness=0.0,            # no harmonics
            spectral_roughness=1.0,           # maximally rough
            nasality=1.0,                     # maximally nasal
            spectral_crest=25.0,              # extremely hard (far from sweet spot)
            hammarberg_index=0.01,            # no low freq → bad depth & booming
            spectral_slope=-25.0,             # maximally steep → bad depth
            spectral_flatness_mean=1.0,       # completely flat → bad warmth
            inharmonicity=1.0,                # completely inharmonic → bad roughness
        )
        result = self.adjuster.calculate(f, audiofeat=af)
        # 极端差组合: quality 低于 20 → -3 或更差
        # 注: -5 理论上可达但需所有维度同时极端差(含矛盾组合),
        # 实际极端差歌声通常在 -3 范围
        assert result.adjustment <= -3, (
            f"Expected adjustment <= -3 with extreme poor timbre, got {result.adjustment}"
        )

    def test_eight_dimension_in_range_randomized(self):
        """八维路径随机值仍在 [-5, +3] 内"""
        import random
        for _ in range(30):
            f = make_features()
            af = _make_audiofeat(
                spectral_centroid_mean=random.uniform(200, 4000),
                harmonic_richness=random.uniform(0.0, 1.0),
                spectral_roughness=random.uniform(0.0, 0.9),
                nasality=random.uniform(0.0, 1.0),
                spectral_crest=random.uniform(0.0, 20.0),
                hammarberg_index=random.uniform(0.0, 3.0),
                spectral_slope=random.uniform(-20.0, 0.0),
                spectral_flatness_mean=random.uniform(0.0, 1.0),
                inharmonicity=random.uniform(0.0, 0.6),
            )
            result = self.adjuster.calculate(f, audiofeat=af)
            assert -5 <= result.adjustment <= 3, (
                f"adjustment={result.adjustment} out of [-5, +3]"
            )

    def test_eight_dimension_confidence_gate_still_works(self):
        """八维路径置信度门控仍然生效"""
        f = make_features(mfcc_cluster_purity=0.01, harmonic_stability=30.0)
        af = _make_audiofeat(
            spectral_centroid_mean=2000.0,
            harmonic_richness=0.7,
            spectral_crest=10.0,
            hammarberg_index=1.0,
        )
        result = self.adjuster.calculate(f, audiofeat=af)
        # 置信度不足 → 归零
        assert result.adjustment == 0

    def test_no_audiofeat_still_uses_heuristic_3dim(self):
        """无 audiofeat → 保持三维护发式路径不变"""
        f = make_features()
        result = self.adjuster.calculate(f, audiofeat=None)
        # 应使用旧的三维护发式路径 (brightness/warmth/nasality)
        assert result.adjustment == 3  # pure timbre
        assert result.is_heuristic is True
