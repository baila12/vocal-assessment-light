"""
Phase A TDD Tests: Dead code removal + Quick mode FeatureFlags fix

RED phase — these tests should fail until Phase A changes are applied.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
_project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_project_root))


class TestFeatureFlagsMode:
    """Verify Quick/Pro mode use correct FeatureFlags."""

    def test_quick_mode_skips_multiscale_hnr(self):
        """Quick mode: enable_multiscale_hnr must be False."""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags.for_quick()
        assert flags.enable_multiscale_hnr is False, (
            "Quick mode should skip multiscale HNR (expensive)"
        )

    def test_quick_mode_skips_reverb_compensation(self):
        """Quick mode: enable_reverb_compensation must be False."""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags.for_quick()
        assert flags.enable_reverb_compensation is False, (
            "Quick mode should skip reverb compensation (expensive)"
        )

    def test_pro_mode_enables_all_advanced(self):
        """Pro mode: all advanced algorithms enabled."""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags.for_professional()
        assert flags.enable_multiscale_hnr is True
        assert flags.enable_reverb_compensation is True
        assert flags.enable_praat_cpp is True
        assert flags.enable_voicing_detection is True

    def test_safe_baseline_disables_all(self):
        """Safe baseline: all advanced features disabled."""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags.safe_baseline()
        assert flags.enable_multiscale_hnr is False
        assert flags.enable_praat_cpp is False
        assert flags.enable_voicing_detection is False
        assert flags.enable_torchcrepe_fallback is False


class TestDeadCodeRemoval:
    """Verify deleted files are truly dead (no production imports)."""

    def test_dl_quality_assessor_not_importable(self):
        """dl_quality_assessor.py must be deleted."""
        with pytest.raises(ImportError):
            from services.dl_services import dl_quality_assessor  # noqa: F401

    def test_emotion_manager_not_importable(self):
        """emotion_manager.py must be deleted."""
        with pytest.raises(ImportError):
            from services.dl_services import emotion_manager  # noqa: F401

    def test_professional_feedback_not_importable(self):
        """professional_feedback.py must be deleted."""
        with pytest.raises(ImportError):
            from services import professional_feedback  # noqa: F401

    def test_audio_comparison_not_importable(self):
        """audio_comparison.py must be deleted."""
        with pytest.raises(ImportError):
            from api.business import audio_comparison  # noqa: F401


class TestDlFieldsRemoved:
    """Verify DL-related fields removed from ScoreResultV4."""

    def test_score_result_no_dl_fields(self):
        """ScoreResultV4 must not have dl_mos_score field."""
        from services.scoring.types import ScoreResultV4
        result = ScoreResultV4()
        assert not hasattr(result, 'dl_mos_score'), (
            "dl_mos_score field must be removed from ScoreResultV4"
        )
        assert not hasattr(result, 'dl_mos_normalized'), (
            "dl_mos_normalized field must be removed"
        )
        assert not hasattr(result, 'dl_method'), (
            "dl_method field must be removed"
        )
        assert not hasattr(result, 'dl_confidence'), (
            "dl_confidence field must be removed"
        )


class TestScoreServiceNoDL:
    """Verify _apply_dl_fusion removed from ScoreServiceV4."""

    def test_no_apply_dl_fusion_method(self):
        """ScoreServiceV4._apply_dl_fusion must not exist."""
        from services.score_service import ScoreServiceV4
        assert not hasattr(ScoreServiceV4, '_apply_dl_fusion'), (
            "_apply_dl_fusion must be removed from ScoreServiceV4"
        )

    def test_calculate_no_dl_params(self):
        """calculate() must not have dl_* parameters."""
        import inspect
        from services.score_service import ScoreServiceV4
        sig = inspect.signature(ScoreServiceV4.calculate)
        params = list(sig.parameters.keys())
        assert 'dl_mos_score' not in params
        assert 'dl_mos_normalized' not in params
        assert 'dl_method' not in params
        assert 'dl_confidence' not in params


class TestAnalyzeAndScoreNoDL:
    """Verify dl_assessor removed from audio_analysis module."""

    def test_no_dl_assessor_module_level(self):
        """audio_analysis module must not have dl_assessor."""
        from api.business import audio_analysis
        assert not hasattr(audio_analysis, 'dl_assessor'), (
            "Module-level dl_assessor must be removed"
        )

    def test_no_assess_with_dl_function(self):
        """_assess_with_dl function must not exist."""
        from api.business import audio_analysis
        assert not hasattr(audio_analysis, '_assess_with_dl'), (
            "_assess_with_dl must be removed"
        )
