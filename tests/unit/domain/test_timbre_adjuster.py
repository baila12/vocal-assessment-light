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
