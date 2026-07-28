"""BreathScorer TDD — 14 tests, port from v6.3 four sub-dimension continuous mapping"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest
from backend.domain.assessment.breath_scorer import BreathScorer, BreathFeatures


def make_features(**kwargs) -> BreathFeatures:
    defaults = {
        "professional_breath_score": 0.0, "long_note_support": 50.0,
        "dynamic_control": 50.0, "breath_design": 50.0, "breath_technique": 50.0,
        "rms_fluctuation": 0.0, "is_artistic_fluctuation": False,
        "controlled_breathiness": 0.0, "uncontrolled_leak": 0.0,
        "breath_breaks": 0, "long_note_count": 0, "soft_segment_count": 0,
        "soft_singing_quality": 0.0, "clean_breath_count": 0, "dynamic_range": 0.0,
        "is_clean_vocal": False,
    }
    defaults.update(kwargs)
    return BreathFeatures(**defaults)


class TestBreathScorer:
    def setup_method(self):
        self.scorer = BreathScorer()

    def test_professional_score_used(self):
        f = make_features(professional_breath_score=85.0)
        result = self.scorer.calculate(f)
        assert result.raw_score == 85.0

    def test_fallback_to_fluctuation_good(self):
        f = make_features(rms_fluctuation=0.15)
        result = self.scorer.calculate(f)
        assert result.raw_score == pytest.approx(100.0, rel=0.05)

    def test_fallback_to_fluctuation_pass(self):
        f = make_features(rms_fluctuation=0.30)
        result = self.scorer.calculate(f)
        assert result.raw_score == pytest.approx(75.0, rel=0.1)

    def test_fallback_to_fluctuation_poor(self):
        f = make_features(rms_fluctuation=0.60)
        result = self.scorer.calculate(f)
        assert result.raw_score < 25

    def test_long_note_excellent_bonus(self):
        f = make_features(professional_breath_score=70.0, long_note_support=85.0)
        result = self.scorer.calculate(f)
        assert result.raw_score >= 70

    def test_long_note_good_no_bonus(self):
        f = make_features(professional_breath_score=70.0, long_note_support=65.0)
        result = self.scorer.calculate(f)
        assert result.raw_score == 70.0  # no bonus

    def test_soft_singing_excellent_bonus(self):
        f = make_features(professional_breath_score=70.0, soft_singing_quality=80.0)
        result = self.scorer.calculate(f)
        assert result.raw_score >= 70

    def test_soft_singing_ok_no_bonus(self):
        f = make_features(professional_breath_score=70.0, soft_singing_quality=55.0)
        result = self.scorer.calculate(f)
        assert result.raw_score == 70.0

    def test_breath_breaks_penalty(self):
        f = make_features(professional_breath_score=80.0, breath_breaks=6)
        result = self.scorer.calculate(f)
        assert result.raw_score < 80

    def test_breath_breaks_capped(self):
        f = make_features(professional_breath_score=80.0, breath_breaks=20)
        result = self.scorer.calculate(f)
        assert result.raw_score >= 65  # penalty capped at 15

    def test_clean_vocal_preserved(self):
        f = make_features(is_clean_vocal=True)
        result = self.scorer.calculate(f)
        assert result.is_clean_vocal is True

    def test_sub_dimensions_preserved(self):
        f = make_features(
            professional_breath_score=75.0,
            long_note_support=80.0, dynamic_control=70.0,
            breath_design=60.0, breath_technique=55.0,
        )
        result = self.scorer.calculate(f)
        assert result.long_note_support == 80.0
        assert result.dynamic_control == 70.0
        assert result.breath_design == 60.0
        assert result.breath_technique == 55.0

    def test_weighted_method(self):
        f = make_features(professional_breath_score=80.0)
        result = self.scorer.calculate(f)
        assert result.weighted() == 80.0 * 0.20

    def test_score_clamped(self):
        f = make_features(rms_fluctuation=3.0, breath_breaks=50)
        result = self.scorer.calculate(f)
        assert 0 <= result.raw_score <= 100


# ================================================================
# v7.3: BreathScorer + audiofeat 增强测试
# ================================================================

def _make_audiofeat(**kwargs):
    """构造 AudiofeatFeatures 测试数据"""
    from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures
    return AudiofeatFeatures(**kwargs)


class TestBreathScorerAudiofeat:
    """BreathScorer audiofeat 增强路径测试 — v7.3"""

    def setup_method(self):
        self.scorer = BreathScorer()

    # ---- 向后兼容 ----

    def test_audiofeat_none_backward_compatible(self):
        """audiofeat=None 时行为不变"""
        f = make_features(professional_breath_score=80.0)
        result = self.scorer.calculate(f, audiofeat=None)
        assert result.raw_score == 80.0

    def test_audiofeat_all_defaults_no_effect(self):
        """全零 audiofeat 不应影响评分"""
        f = make_features(professional_breath_score=75.0)
        af = _make_audiofeat()  # all zeros
        result = self.scorer.calculate(f, audiofeat=af)
        assert result.raw_score == 75.0

    # ---- GNE (Glottal-to-Noise Excitation) ----

    def test_audiofeat_gne_low_with_low_hnr_penalizes(self):
        """GNE<0.4 且 HNR<10 → 不可控漏气惩罚"""
        f = make_features(professional_breath_score=75.0)
        af = _make_audiofeat(gne_mean=0.3, hnr_mean=8.0)
        result = self.scorer.calculate(f, audiofeat=af)
        assert result.raw_score < 75.0  # should penalize

    def test_audiofeat_gne_high_quality_bonus(self):
        """GNE>0.8 且 CPPS>10 → 优秀声门控制加分"""
        f = make_features(professional_breath_score=75.0)
        af = _make_audiofeat(gne_mean=0.85, cpp_mean=12.0)
        result = self.scorer.calculate(f, audiofeat=af)
        assert result.raw_score >= 75.0  # bonus should apply

    def test_audiofeat_gne_moderate_no_effect(self):
        """GNE 0.5-0.7 → 不触发增强"""
        f = make_features(professional_breath_score=75.0)
        af = _make_audiofeat(gne_mean=0.6, hnr_mean=12.0)
        result = self.scorer.calculate(f, audiofeat=af)
        assert result.raw_score == 75.0  # no change

    # ---- CPPS ----

    def test_audiofeat_cpp_very_low_indicates_weak_support(self):
        """CPPS<3 → 声门闭合极弱, 扣分"""
        f = make_features(professional_breath_score=75.0)
        af = _make_audiofeat(cpp_mean=2.0)
        result = self.scorer.calculate(f, audiofeat=af)
        assert result.raw_score < 75.0

    # ---- HNR_praat ----

    def test_audiofeat_hnr_very_low_with_gne_penalizes(self):
        """HNR<5 且 GNE低 → 组合惩罚"""
        f = make_features(professional_breath_score=70.0)
        af_combined = _make_audiofeat(hnr_mean=3.0, gne_mean=0.2)
        result_combined = self.scorer.calculate(f, audiofeat=af_combined)
        # 组合 (HNR低 + GNE低) 应惩罚
        assert result_combined.raw_score < 70.0
        # 无 audiofeat 对比：惩罚后分数应低于无 audiofeat
        result_no_af = self.scorer.calculate(f, audiofeat=None)
        assert result_combined.raw_score < result_no_af.raw_score

    # ---- Score clamping ----

    def test_audiofeat_enhanced_score_in_range(self):
        """增强后分数仍在 [0, 100]"""
        f = make_features(professional_breath_score=95.0)
        af = _make_audiofeat(gne_mean=0.95, cpp_mean=15.0, hnr_mean=25.0)
        result = self.scorer.calculate(f, audiofeat=af)
        assert 0.0 <= result.raw_score <= 100.0
