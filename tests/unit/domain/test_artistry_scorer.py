"""ArtistryScorer TDD — 8 tests, port from v6.1 independent acoustic features"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest
from backend.domain.assessment.artistry_scorer import ArtistryScorer, ArtistryFeatures


def make_features(**kwargs) -> ArtistryFeatures:
    defaults = {
        "vibrato_quality": 50.0, "vibrato_count": 3,
        "dynamic_range": 15.0, "crescendo_quality": 50.0,
        "phrase_coherence": 50.0, "is_artistic_fluctuation": False,
        "long_note_count": 2, "pitch_cv": 0.06,
    }
    defaults.update(kwargs)
    return ArtistryFeatures(**defaults)


class TestArtistryScorer:
    def setup_method(self):
        self.scorer = ArtistryScorer()

    def test_vibrato_excellent(self):
        f = make_features(vibrato_quality=95.0, vibrato_count=8)
        result = self.scorer.calculate(f)
        assert result.vibrato_quality > 80

    def test_vibrato_none(self):
        f = make_features(vibrato_quality=0.0, vibrato_count=0)
        result = self.scorer.calculate(f)
        assert result.vibrato_quality == 0.0

    def test_dynamic_rich(self):
        f = make_features(dynamic_range=25.0, crescendo_quality=80.0)
        result = self.scorer.calculate(f)
        assert result.dynamic_control > 70

    def test_phrase_excellent(self):
        f = make_features(
            phrase_coherence=90.0, is_artistic_fluctuation=True, long_note_count=4
        )
        result = self.scorer.calculate(f)
        assert result.phrase_expression > 80

    def test_phrase_basic(self):
        f = make_features(phrase_coherence=40.0, long_note_count=0)
        result = self.scorer.calculate(f)
        assert result.phrase_expression < 40

    def test_pitch_variation_natural(self):
        f = make_features(pitch_cv=0.08)
        result = self.scorer.calculate(f)
        assert result.pitch_variation > 20

    def test_weighted_method(self):
        f = make_features()
        result = self.scorer.calculate(f)
        assert result.weighted() == result.raw_score * 0.10

    def test_combined_weighted(self):
        f = make_features(
            vibrato_quality=80.0, vibrato_count=5,
            dynamic_range=20.0, crescendo_quality=70.0,
            phrase_coherence=80.0, is_artistic_fluctuation=True,
            pitch_cv=0.08,
        )
        result = self.scorer.calculate(f)
        assert 0 <= result.raw_score <= 100
        assert isinstance(result.raw_score, float)
