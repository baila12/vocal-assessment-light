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
