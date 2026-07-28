"""TechniqueScorer TDD — 10 tests, v7.0 refactored: articulation + breath-voice ratio"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest
from backend.domain.assessment.technique_scorer import TechniqueScorer, TechniqueFeatures


def make_features(**kwargs) -> TechniqueFeatures:
    defaults = {
        "onset_density": 3.0, "spectral_flux": 1.0, "consonant_clarity": 50.0,
        "hnr_mean": 18.0, "spectral_tilt": 0.0, "hf_energy_ratio": 0.4, "cpp_mean": 1.5,
    }
    defaults.update(kwargs)
    return TechniqueFeatures(**defaults)


class TestTechniqueScorer:
    def setup_method(self):
        self.scorer = TechniqueScorer()

    def test_articulation_perfect(self):
        f = make_features(consonant_clarity=100.0, onset_density=3.0, spectral_flux=1.0)
        result = self.scorer.calculate(f)
        assert result.articulation_clarity >= 60

    def test_articulation_poor(self):
        f = make_features(consonant_clarity=20.0, onset_density=0.3, spectral_flux=8.0)
        result = self.scorer.calculate(f)
        assert result.articulation_clarity < 40

    def test_breath_voice_ratio_optimal(self):
        f = make_features(hnr_mean=18.0, spectral_tilt=0.0, hf_energy_ratio=0.4)
        result = self.scorer.calculate(f)
        assert result.breath_voice_ratio >= 70

    def test_breath_voice_ratio_breathy(self):
        f = make_features(hnr_mean=4.0, spectral_tilt=-8.0, hf_energy_ratio=0.8)
        result = self.scorer.calculate(f)
        assert result.breath_voice_ratio < 50

    def test_breath_voice_ratio_unnatural_high(self):
        f = make_features(hnr_mean=35.0)
        result = self.scorer.calculate(f)
        assert result.breath_voice_ratio < 90  # too "hard" = unnatural

    def test_combined_5050_weighting(self):
        f = make_features(consonant_clarity=60.0, hnr_mean=18.0)
        result = self.scorer.calculate(f)
        # ~55 articulation * 0.5 + ~70 bvr * 0.5 = ~62.5
        assert 60 <= result.raw_score <= 85

    def test_hnr_mean_preserved(self):
        f = make_features(hnr_mean=15.0)
        result = self.scorer.calculate(f)
        assert result.hnr_mean == 15.0

    def test_cpp_mean_preserved(self):
        f = make_features(cpp_mean=2.0)
        result = self.scorer.calculate(f)
        assert result.cpp_mean == 2.0

    def test_weighted_method(self):
        f = make_features()
        result = self.scorer.calculate(f)
        assert result.weighted() == result.raw_score * 0.25

    def test_score_clamped(self):
        f = make_features(consonant_clarity=0.0, hnr_mean=0.0, spectral_tilt=-20.0)
        result = self.scorer.calculate(f)
        assert 0 <= result.raw_score <= 100


# ================================================================
# v7.3: TechniqueScorer + audiofeat 增强测试
# ================================================================

def _make_audiofeat(**kwargs):
    """构造 AudiofeatFeatures 测试数据"""
    from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures
    return AudiofeatFeatures(**kwargs)


class TestTechniqueScorerAudiofeat:
    """TechniqueScorer audiofeat 增强路径测试 — v7.3"""

    def setup_method(self):
        self.scorer = TechniqueScorer()

    # ---- 向后兼容 ----

    def test_audiofeat_none_backward_compatible(self):
        """audiofeat=None 时行为不变"""
        f = make_features(consonant_clarity=60.0, hnr_mean=18.0)
        result = self.scorer.calculate(f, audiofeat=None)
        assert 60 <= result.raw_score <= 85

    def test_audiofeat_all_defaults_no_effect(self):
        """全零 audiofeat 不应影响评分"""
        f = make_features(consonant_clarity=60.0, hnr_mean=18.0)
        result_no_af = self.scorer.calculate(f)
        af = _make_audiofeat()
        result_with_af = self.scorer.calculate(f, audiofeat=af)
        assert result_with_af.raw_score == result_no_af.raw_score

    # ---- Jitter (频率微扰) ----

    def test_audiofeat_jitter_low_boosts_articulation(self):
        """Jitter<0.5% → 极稳定咬字, 加分"""
        f = make_features(consonant_clarity=50.0)
        af = _make_audiofeat(jitter_local=0.3)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score > result_no_af.raw_score

    def test_audiofeat_jitter_high_penalizes_articulation(self):
        """Jitter>3% → 频率不稳定, 扣分"""
        f = make_features(consonant_clarity=50.0, hnr_mean=18.0)
        af = _make_audiofeat(jitter_local=4.0)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score < result_no_af.raw_score

    # ---- Shimmer (幅度微扰) ----

    def test_audiofeat_shimmer_low_boosts_breath_voice(self):
        """Shimmer<0.1dB → 极稳定振幅, 加分"""
        f = make_features(hnr_mean=18.0)
        af = _make_audiofeat(shimmer_db=0.05)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score > result_no_af.raw_score

    def test_audiofeat_shimmer_high_penalizes(self):
        """Shimmer>0.5dB → 振幅不稳定, 扣分"""
        f = make_features(hnr_mean=18.0)
        af = _make_audiofeat(shimmer_db=0.7)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score < result_no_af.raw_score

    # ---- Closed Quotient (声门闭合商) ----

    def test_audiofeat_closed_quotient_optimal_boosts(self):
        """CQ 0.4-0.6 → 高效发声, 加分"""
        f = make_features(hnr_mean=18.0)
        af = _make_audiofeat(closed_quotient=0.5)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score > result_no_af.raw_score

    def test_audiofeat_closed_quotient_low_penalizes(self):
        """CQ<0.2 → 声门闭合不足, 扣分"""
        f = make_features(hnr_mean=18.0)
        af = _make_audiofeat(closed_quotient=0.1)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score < result_no_af.raw_score

    # ---- Score clamping ----

    def test_audiofeat_enhanced_score_in_range(self):
        """增强后分数仍在 [0, 100]"""
        f = make_features(consonant_clarity=90.0, hnr_mean=25.0)
        af = _make_audiofeat(jitter_local=0.1, shimmer_db=0.02, closed_quotient=0.55)
        result = self.scorer.calculate(f, audiofeat=af)
        assert 0.0 <= result.raw_score <= 100.0
