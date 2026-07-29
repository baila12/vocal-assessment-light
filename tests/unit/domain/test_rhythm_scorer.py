"""RhythmScorer TDD — 12 tests, port from v6.3 onset CV + irregularity"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest
from backend.domain.assessment.rhythm_scorer import RhythmScorer, RhythmFeatures
from backend.domain.assessment.value_objects import RhythmScore


def make_features(**kwargs) -> RhythmFeatures:
    defaults = {
        "avg_deviation_ratio": 0.0,
        "irregularity": 0.0,
        "onset_density": 2.0,
        "onset_count": 100,
        "off_beat_segments": 0,
        "is_clean_vocal": False,
    }
    defaults.update(kwargs)
    return RhythmFeatures(**defaults)


class TestRhythmScorer:
    def setup_method(self):
        self.scorer = RhythmScorer()

    # 1. Perfect deviation → ~100
    def test_perfect_deviation(self):
        f = make_features(avg_deviation_ratio=0.0)
        result = self.scorer.calculate(f)
        assert result.raw_score == pytest.approx(100, rel=0.05)
        assert result.onset_cv == 0.0

    # 2. Good deviation → ~90
    def test_good_deviation(self):
        f = make_features(avg_deviation_ratio=0.15)
        result = self.scorer.calculate(f)
        assert 85 <= result.raw_score <= 100

    # 3. Pass boundary deviation → ~65
    def test_pass_deviation(self):
        f = make_features(avg_deviation_ratio=0.25)
        result = self.scorer.calculate(f)
        assert 50 <= result.raw_score <= 85

    # 4. Poor deviation
    def test_poor_deviation(self):
        f = make_features(avg_deviation_ratio=0.40)
        result = self.scorer.calculate(f)
        assert result.raw_score < 60

    # 5. No irregularity → no penalty
    def test_no_irregularity_penalty(self):
        f = make_features(irregularity=0.3)
        result = self.scorer.calculate(f)
        assert result.irregularity_penalty == 0.0

    # 6. Light irregularity → penalty ~1.5
    def test_light_irregularity(self):
        f = make_features(irregularity=0.6)
        result = self.scorer.calculate(f)
        assert 0 < result.irregularity_penalty <= 5
        assert result.raw_score < 100

    # 7. Medium irregularity → penalty ~9.5
    def test_medium_irregularity(self):
        f = make_features(irregularity=1.0)
        result = self.scorer.calculate(f)
        assert 4 <= result.irregularity_penalty <= 15

    # 8. Heavy irregularity → penalty ~17.5
    def test_heavy_irregularity(self):
        f = make_features(irregularity=1.5)
        result = self.scorer.calculate(f)
        assert result.irregularity_penalty > 10

    # 9. Irregularity penalty capped at 25
    def test_irregularity_penalty_capped(self):
        f = make_features(irregularity=3.0)
        result = self.scorer.calculate(f)
        assert result.irregularity_penalty <= 25

    # 10. Clean vocal → no extra effect on score
    def test_clean_vocal_no_effect(self):
        f_clean = make_features(is_clean_vocal=True)
        f_dirty = make_features(is_clean_vocal=False)
        r_clean = self.scorer.calculate(f_clean)
        r_dirty = self.scorer.calculate(f_dirty)
        assert r_clean.raw_score == r_dirty.raw_score
        assert r_clean.is_clean_vocal is True

    # 11. Weighted method
    def test_weighted_method(self):
        f = make_features()
        result = self.scorer.calculate(f)
        assert result.weighted() == result.raw_score * 0.12  # v7.4: 10%→12%

    # 12. Score clamped
    def test_score_clamped(self):
        f = make_features(avg_deviation_ratio=2.0, irregularity=5.0)
        result = self.scorer.calculate(f)
        assert 0 <= result.raw_score <= 100
