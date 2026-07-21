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
