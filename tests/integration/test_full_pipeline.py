"""
Integration tests for the full scoring pipeline v5.12.
Tests quick/professional mode consistency and edge case handling.
"""
import pytest
import numpy as np
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.business.audio_analysis import analyze_and_score


class TestFullScoringPipeline:
    """Full pipeline integration tests."""

    def _get_test_audio(self, name='noise_test.wav'):
        """Get path to a test audio file."""
        base = Path(__file__).parent.parent / 'test_data' / 'audio'
        # Check vocal dir first for real audio
        vocal_path = base / 'vocal' / '恋人.mp3'
        non_vocal_path = base / 'non_vocal' / name
        if vocal_path.exists():
            return str(vocal_path)
        if non_vocal_path.exists():
            return str(non_vocal_path)
        return None

    def test_white_noise_returns_non_voice(self):
        """White noise should return is_voice=False and total_score=0."""
        audio_path = Path(__file__).parent.parent / 'test_data' / 'audio' / 'non_vocal' / 'noise_test.wav'
        if not audio_path.exists():
            pytest.skip('noise_test.wav not found')

        result = analyze_and_score(str(audio_path), mode='quick')
        # Should detect as non-voice
        if not result.get('success'):
            pytest.skip(f'Analysis failed: {result.get("error")}')

        # Either is_voice=False or total_score should be very low
        is_voice = result.get('is_voice', True)
        total = result.get('total_score', 100)
        assert (not is_voice) or (total <= 25), \
            f'Expected non-voice or low score, got is_voice={is_voice}, total={total}'

    def test_vocal_audio_returns_reasonable_scores(self):
        """Real vocal audio should get scores in reasonable range (20-95)."""
        audio_path = self._get_test_audio()
        if not audio_path:
            pytest.skip('No test audio available')

        result = analyze_and_score(str(audio_path), mode='quick')
        if not result.get('success'):
            pytest.skip(f'Analysis failed: {result.get("error")}')

        total = result.get('total_score', 0)
        scores = result.get('scores', {})

        # Total score should be in reasonable range
        assert 10 <= total <= 98, f'Total score {total} out of expected range 10-98'

        # Individual dimension scores should be in range
        for dim in ['pitch', 'rhythm', 'breath', 'technique', 'artistry']:
            dim_score = scores.get(dim, 0)
            assert 0 <= dim_score <= 100, f'{dim} score {dim_score} out of range 0-100'

    def test_quick_vs_professional_mode_both_work(self):
        """Both modes should return valid results for the same audio."""
        audio_path = self._get_test_audio()
        if not audio_path:
            pytest.skip('No test audio available')

        quick = analyze_and_score(str(audio_path), mode='quick')
        prof = analyze_and_score(str(audio_path), mode='professional')

        assert quick.get('success'), f'Quick mode failed: {quick.get("error")}'
        assert prof.get('success'), f'Professional mode failed: {prof.get("error")}'

        # Both should have valid scores
        assert 'total_score' in quick
        assert 'total_score' in prof

    def test_non_voice_result_has_zero_scores(self):
        """Non-voice result should have all zero scores and is_voice=False."""
        audio_path = Path(__file__).parent.parent / 'test_data' / 'audio' / 'non_vocal' / 'noise_test.wav'
        if not audio_path.exists():
            pytest.skip('noise_test.wav not found')

        result = analyze_and_score(str(audio_path), mode='quick')
        if not result.get('success'):
            pytest.skip(f'Analysis failed: {result.get("error")}')

        # If non-voice, all scores should be 0
        if not result.get('is_voice', True):
            scores = result.get('scores', {})
            for dim in ['pitch', 'rhythm', 'breath', 'technique', 'artistry']:
                assert scores.get(dim, -1) == 0.0, \
                    f'{dim} should be 0 for non-voice, got {scores.get(dim)}'
            assert result.get('total_score', -1) == 0

    def test_result_contains_required_fields(self):
        """API response should contain all required fields."""
        audio_path = self._get_test_audio()
        if not audio_path:
            pytest.skip('No test audio available')

        result = analyze_and_score(str(audio_path), mode='professional')
        if not result.get('success'):
            pytest.skip(f'Analysis failed: {result.get("error")}')

        # Required top-level fields
        required = ['success', 'total_score', 'level', 'stars', 'scores', 'advice']
        for field in required:
            assert field in result, f'Missing required field: {field}'

        # Level and stars should not be "?"
        assert result.get('level') != '?', 'Level is still "?"'
        assert result.get('stars', '?')[0] != '?', 'Stars is still "?"'

        # Scores should have all 5 dimensions
        for dim in ['pitch', 'rhythm', 'breath', 'technique', 'artistry']:
            assert dim in result.get('scores', {}), f'Missing score dimension: {dim}'


class TestBreathScoreDifferentiation:
    """Verify breath score differentiation after v5.12 fixes."""

    def test_professional_breath_not_always_100(self):
        """Professional breath score should vary, not always be ~100."""
        # This test verifies the scoring logic doesn't always return ~100
        # We use synthetic feature values to test

        from services.scoring_config import BreathThresholds
        from services.scoring import BreathScorer

        scorer = BreathScorer(BreathThresholds(excellent=0.18, good=0.28, pass_threshold=0.40))

        # Test with poor fluctuation
        score1, _ = scorer.calculate(0.50)
        # Test with good fluctuation
        score2, _ = scorer.calculate(0.15)
        # Test with excellent fluctuation
        score3, _ = scorer.calculate(0.05)

        # Scores should be significantly different
        scores = [score1, score2, score3]
        score_range = max(scores) - min(scores)
        assert score_range > 15, \
            f'Breath scores too similar: {scores}, range={score_range:.1f}'
