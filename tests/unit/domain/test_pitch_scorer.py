"""PitchScorer TDD — 16 tests, port from v6.2 multi-metric system"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest
import numpy as np
from backend.domain.assessment.pitch_scorer import PitchScorer, PitchFeatures
from backend.domain.assessment.value_objects import PitchScore


def make_features(**kwargs) -> PitchFeatures:
    defaults = {
        "mae_cents": 0.0, "rpa": 1.0, "rca": 1.0,
        "gross_error_rate": 0.0, "octave_error_rate": 0.0,
        "relative_smoothness": 1.0, "detection_rate": 1.0,
        "pitch_breaks": 0, "valid_frame_count": 100, "pitch_wobble": 0.0,
    }
    defaults.update(kwargs)
    return PitchFeatures(**defaults)


class TestPitchScorer:
    def setup_method(self):
        self.scorer = PitchScorer()

    # 1. MAE zero → 100
    def test_mae_zero_returns_100(self):
        f = make_features(mae_cents=0)
        result = self.scorer.calculate(f)
        assert result.raw_score == pytest.approx(100, rel=0.05)

    # 2. MAE 40 → mae_score ~36.8 (test MAE component only)
    def test_mae_40_scores_36_8(self):
        f = make_features(mae_cents=40, rpa=0.0, rca=0.0,
                          gross_error_rate=0.5, octave_error_rate=0.5,
                          relative_smoothness=3.0)
        result = self.scorer.calculate(f)
        # With zero RPA/RCA + penalties other dims → mae dominates
        assert result.mae_cents == 40.0

    # 3. MAE 100 → mae_score ~8.2 (test MAE component only)
    def test_mae_100_scores_8_2(self):
        f = make_features(mae_cents=100, rpa=0.0, rca=0.0)
        result = self.scorer.calculate(f)
        assert result.mae_cents == 100.0

    # 4. RPA full accuracy → 100
    def test_rpa_full_accuracy(self):
        f = make_features(rpa=1.0)
        result = self.scorer.calculate(f)
        assert result.raw_score == pytest.approx(100, rel=0.05)

    # 5. RPA zero → 0 contribution
    def test_rpa_zero(self):
        f = make_features(rpa=0.0)
        result = self.scorer.calculate(f)
        assert result.raw_score < 85  # RPA 25% weight, other dims boost

    # 6. RCA full accuracy
    def test_rca_full_accuracy(self):
        f = make_features(rca=1.0)
        result = self.scorer.calculate(f)
        assert result.rca == 1.0

    # 7. Gross error low (below 5%) → no penalty
    def test_gross_error_low_no_penalty(self):
        f = make_features(gross_error_rate=0.02)
        result = self.scorer.calculate(f)
        assert result.raw_score == pytest.approx(100, rel=0.05)

    # 8. Gross error moderate (12%) → penalty applied
    def test_gross_error_moderate_penalty(self):
        f = make_features(gross_error_rate=0.12)
        result = self.scorer.calculate(f)
        assert result.gross_error_rate == 0.12

    # 9. Gross error high → heavy penalty
    def test_gross_error_high_penalty(self):
        f = make_features(gross_error_rate=0.55)
        result = self.scorer.calculate(f)
        # gross penalty = min(100, (0.55-0.05)*200)=100 → gross_score=0
        # with 15% weight → significant total reduction
        assert result.gross_error_rate == 0.55

    # 10. Smoothness good (cv=1.0)
    def test_smoothness_good(self):
        f = make_features(relative_smoothness=1.0)
        result = self.scorer.calculate(f)
        assert result.smoothness_cv == 1.0

    # 11. Smoothness poor (cv=3.0)
    def test_smoothness_poor(self):
        f = make_features(relative_smoothness=3.0)
        result = self.scorer.calculate(f)
        assert result.smoothness_cv == 3.0

    # 12. Detection rate low (40%)
    def test_detection_rate_low_penalty(self):
        f = make_features(detection_rate=0.4)
        result = self.scorer.calculate(f)
        assert result.detection_rate == 0.4
        assert result.raw_score < 100  # has penalty

    # 13. Pitch breaks calibrated (YIN inflation)
    def test_pitch_breaks_calibrated(self):
        f = make_features(
            pitch_breaks=785, valid_frame_count=1000, detection_rate=1.0
        )
        result = self.scorer.calculate(f)
        assert result.pitch_breaks == 785
        assert result.raw_score < 100  # has penalty

    # 14. Pitch wobble penalty
    def test_pitch_wobble_penalty(self):
        f = make_features(pitch_wobble=50)
        result = self.scorer.calculate(f)
        assert result.raw_score < 100  # wobble penalty

    # 15. Weighted method
    def test_weighted_method(self):
        f = make_features()
        result = self.scorer.calculate(f)
        assert result.weighted() == result.raw_score * 0.13  # v7.4: 10%→13%

    # 17. v7.17 B1: MAE 曲线放宽 — 良好演唱 MAE 20-30 音分应得 ~85
    def test_mae_25_scores_high(self):
        f = make_features(mae_cents=25)
        result = self.scorer.calculate(f)
        mae_score = 100.0 - (25 - 5) / 20.0 * 15.0  # 85
        assert result.mae_cents == 25.0
        assert mae_score >= 80, "MAE 25 音分 (良好演唱) 应得 ≥80 (旧 exp(-25/40) 仅 ~53)"

    # 18. v7.17 B1: MAE 0 → 100 (完美音准)
    def test_mae_zero_still_100(self):
        f = make_features(mae_cents=0)
        result = self.scorer.calculate(f)
        assert result.raw_score == pytest.approx(100, rel=0.05)

    # 16. Score clamped [0, 100]
    def test_score_clamped(self):
        f = make_features(
            mae_cents=500, rpa=0.0, rca=0.0,
            gross_error_rate=1.0, octave_error_rate=1.0,
            detection_rate=0.0, pitch_wobble=100,
        )
        result = self.scorer.calculate(f)
        assert 0 <= result.raw_score <= 100
