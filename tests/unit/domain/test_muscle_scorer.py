"""MuscleStrengthScorer TDD — 12 tests, NEW heuristic proxy indicators"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest
from backend.domain.assessment.muscle_scorer import MuscleStrengthScorer, MuscleFeatures


def make_features(**kwargs) -> MuscleFeatures:
    defaults = {
        "max_db_level": -10.0, "low_freq_energy_ratio": 0.30,
        "rms_decay_rate": 1.0, "singers_formant_energy": 0.08,
        "formant_clustering_quality": 50.0, "overtone_richness": 5.0,
        "dynamic_range_db": 15.0,
    }
    defaults.update(kwargs)
    return MuscleFeatures(**defaults)


class TestMuscleStrengthScorer:
    def setup_method(self):
        self.scorer = MuscleStrengthScorer()

    def test_body_good_support(self):
        f = make_features(rms_decay_rate=0.3, max_db_level=-8.0, low_freq_energy_ratio=0.45)
        result = self.scorer.calculate(f)
        assert result.body_muscle_strength > 70

    def test_body_weak_support(self):
        f = make_features(rms_decay_rate=2.5, max_db_level=-25.0, low_freq_energy_ratio=0.05)
        result = self.scorer.calculate(f)
        assert result.body_muscle_strength < 40

    def test_body_wide_dynamic_range_bonus(self):
        f = make_features(dynamic_range_db=35.0)
        result = self.scorer.calculate(f)
        assert result.body_muscle_strength > 50  # bonus applied

    def test_facial_strong_formant(self):
        f = make_features(singers_formant_energy=0.20, formant_clustering_quality=85.0, overtone_richness=10.0)
        result = self.scorer.calculate(f)
        assert result.facial_muscle_strength > 70

    def test_facial_weak_formant(self):
        f = make_features(singers_formant_energy=0.01, formant_clustering_quality=10.0, overtone_richness=1.0)
        result = self.scorer.calculate(f)
        assert result.facial_muscle_strength < 40

    def test_facial_rich_overtone(self):
        f = make_features(overtone_richness=12.0)
        result = self.scorer.calculate(f)
        assert result.facial_muscle_strength > 50

    def test_combined_5050_weighting(self):
        f = make_features(
            max_db_level=-5.0, low_freq_energy_ratio=0.45, rms_decay_rate=0.3,
            singers_formant_energy=0.01, formant_clustering_quality=10.0, overtone_richness=1.0,
        )
        result = self.scorer.calculate(f)
        assert result.body_muscle_strength > 70
        assert result.facial_muscle_strength < 40
        assert result.raw_score == pytest.approx(
            result.body_muscle_strength * 0.50 + result.facial_muscle_strength * 0.50, rel=0.05
        )

    def test_max_db_mapping_boundaries(self):
        r1 = self.scorer.calculate(make_features(max_db_level=-30.0))
        r2 = self.scorer.calculate(make_features(max_db_level=-20.0))
        r3 = self.scorer.calculate(make_features(max_db_level=-10.0))
        r4 = self.scorer.calculate(make_features(max_db_level=0.0))
        assert r1.body_muscle_strength < r2.body_muscle_strength < r3.body_muscle_strength < r4.body_muscle_strength

    def test_decay_rate_mapping(self):
        r1 = self.scorer.calculate(make_features(rms_decay_rate=0.3))
        r2 = self.scorer.calculate(make_features(rms_decay_rate=1.5))
        r3 = self.scorer.calculate(make_features(rms_decay_rate=3.5))
        assert r1.body_muscle_strength > r2.body_muscle_strength > r3.body_muscle_strength

    def test_score_clamped(self):
        f = make_features(
            max_db_level=10.0, low_freq_energy_ratio=1.0, rms_decay_rate=0.1,
            singers_formant_energy=1.0, formant_clustering_quality=100.0, overtone_richness=20.0,
            dynamic_range_db=50.0,
        )
        result = self.scorer.calculate(f)
        assert 0 <= result.raw_score <= 100

    def test_is_heuristic_always_true(self):
        f = make_features()
        result = self.scorer.calculate(f)
        assert result.is_heuristic is True

    def test_weighted_method(self):
        f = make_features()
        result = self.scorer.calculate(f)
        assert result.weighted() == result.raw_score * 0.25


# ================================================================
# v7.3: MuscleStrengthScorer + audiofeat 增强测试
# ================================================================

def _make_audiofeat(**kwargs):
    """构造 AudiofeatFeatures 测试数据"""
    from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures
    return AudiofeatFeatures(**kwargs)


class TestMuscleScorerAudiofeat:
    """MuscleStrengthScorer audiofeat 增强路径测试 — v7.3"""

    def setup_method(self):
        self.scorer = MuscleStrengthScorer()

    # ---- 向后兼容 ----

    def test_audiofeat_none_backward_compatible(self):
        """audiofeat=None 时行为不变"""
        f = make_features(max_db_level=-10.0, rms_decay_rate=1.0)
        result = self.scorer.calculate(f, audiofeat=None)
        assert 0 <= result.raw_score <= 100

    def test_audiofeat_all_defaults_no_effect(self):
        """全零 audiofeat 不影响评分"""
        f = make_features()
        result_no_af = self.scorer.calculate(f)
        af = _make_audiofeat()
        result_with_af = self.scorer.calculate(f, audiofeat=af)
        assert result_with_af.raw_score == result_no_af.raw_score

    # ---- Soft Phonation (身体力量代理) ----

    def test_audiofeat_soft_phonation_high_penalizes(self):
        """高软发声指数 → 支撑不足, 扣分"""
        f = make_features(max_db_level=-10.0, rms_decay_rate=1.0)
        af = _make_audiofeat(soft_phonation_mean=0.8)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.body_muscle_strength < result_no_af.body_muscle_strength

    # ---- Vocal Fry (身体力量代理) ----

    def test_audiofeat_vocal_fry_excessive_penalizes(self):
        """高气泡音占比 → 可能支撑不足, 扣分"""
        f = make_features(max_db_level=-10.0, rms_decay_rate=1.0)
        af = _make_audiofeat(vocal_fry_ratio=0.5)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.body_muscle_strength < result_no_af.body_muscle_strength

    # ---- Hammarberg Index (面部力量代理) ----

    def test_audiofeat_hammarberg_enhances_facial(self):
        """Hammarberg 反映低频/高频能量平衡 → 面部共鸣评估"""
        f = make_features(singers_formant_energy=0.08)
        af = _make_audiofeat(hammarberg_index=20.0)
        result = self.scorer.calculate(f, audiofeat=af)
        # Hammarberg 高 = 低频能量强 = 胸腔共鸣好
        assert result.facial_muscle_strength > 0

    # ---- 组合测试 ----

    def test_audiofeat_enhanced_score_in_range(self):
        """增强后分数仍在 [0, 100]"""
        f = make_features()
        af = _make_audiofeat(
            soft_phonation_mean=0.3, vocal_fry_ratio=0.1,
            hammarberg_index=15.0, rms_energy=0.5,
        )
        result = self.scorer.calculate(f, audiofeat=af)
        assert 0.0 <= result.raw_score <= 100.0
        assert result.is_heuristic is True
