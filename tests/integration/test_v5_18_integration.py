"""
v5.18 新算法端到端集成测试

测试 FeatureFlags 实际影响评分管线的行为。
所有测试应在 flag 接入管线后从 RED 变为 GREEN。
"""
import pytest
import numpy as np
from pathlib import Path

from services.feature_flags import FeatureFlags

pytestmark = pytest.mark.integration


class TestAudioFeaturesServiceIntegration:

    def _make_harmonic_signal(self, sr=22050, dur=2.0):
        t = np.linspace(0, dur, int(sr * dur), endpoint=False)
        signal = np.zeros_like(t)
        for h in range(1, 8):
            signal += (0.3 / h) * np.sin(2 * np.pi * 220 * h * t)
        return signal / np.max(np.abs(signal)) * 0.5

    def test_multiscale_hnr_flag_changes_hnr_significantly(self):
        """enable_multiscale_hnr=True 时 HNR 变化 > 1.0 dB"""
        from services.audio_features_service import AudioFeaturesService

        service = AudioFeaturesService(sample_rate=22050)
        signal = self._make_harmonic_signal()

        result_off = service.extract_all_features(
            signal, feature_flags=FeatureFlags()
        )
        result_on = service.extract_all_features(
            signal, feature_flags=FeatureFlags(enable_multiscale_hnr=True)
        )

        diff = abs(result_on.hnr - result_off.hnr)
        assert diff > 1.0, f"HNR diff={diff:.2f}, expected > 1.0"

    def test_praat_cpp_flag_changes_cpp_significantly(self):
        """enable_praat_cpp=True 时 CPP 变化 > 0.01"""
        from services.audio_features_service import AudioFeaturesService

        service = AudioFeaturesService(sample_rate=22050)
        signal = self._make_harmonic_signal()

        result_off = service.extract_all_features(
            signal, feature_flags=FeatureFlags()
        )
        result_on = service.extract_all_features(
            signal, feature_flags=FeatureFlags(enable_praat_cpp=True)
        )

        diff = abs(result_on.cpp - result_off.cpp)
        assert diff > 0.01, f"CPP diff={diff:.6f}, expected > 0.01"

    def test_both_flags_on_both_values_change(self):
        """两个 flag 开启后 HNR 和 CPP 都应显著变化"""
        from services.audio_features_service import AudioFeaturesService

        service = AudioFeaturesService(sample_rate=22050)
        signal = self._make_harmonic_signal()

        result_off = service.extract_all_features(
            signal, feature_flags=FeatureFlags()
        )
        result_on = service.extract_all_features(
            signal, feature_flags=FeatureFlags(
                enable_multiscale_hnr=True, enable_praat_cpp=True
            )
        )

        hnr_diff = abs(result_on.hnr - result_off.hnr)
        cpp_diff = abs(result_on.cpp - result_off.cpp)
        assert hnr_diff > 1.0, f"HNR diff={hnr_diff:.2f}"
        assert cpp_diff > 0.01, f"CPP diff={cpp_diff:.6f}"
        assert result_on.success is True


class TestScorePipelineIntegration:

    @pytest.fixture
    def test_audio(self):
        p = Path(__file__).parent.parent.parent / "uploads" / "melody.wav"
        return str(p) if p.exists() else None

    def test_default_flags_unchanged(self, test_audio):
        """默认 flags 关闭时评分不变 (回归保护)"""
        if not test_audio:
            pytest.skip("melody.wav not found")
        from api.business.audio_analysis import analyze_and_score

        r1 = analyze_and_score(test_audio, mode='quick', feature_flags=FeatureFlags())
        r2 = analyze_and_score(test_audio, mode='quick', feature_flags=FeatureFlags())

        if not r1.get('is_voice'):
            pytest.skip("Audio not detected as voice")

        s1, s2 = r1.get('scores', {}), r2.get('scores', {})
        for dim in ['pitch', 'rhythm', 'breath', 'technique', 'artistry']:
            assert s1.get(dim) == s2.get(dim), \
                f"{dim}: {s1.get(dim)} vs {s2.get(dim)}"

    def test_flags_on_changes_technique_score(self, test_audio):
        """flag 开启后 Technique 分数应变化 > 0.5"""
        if not test_audio:
            pytest.skip("melody.wav not found")
        from api.business.audio_analysis import analyze_and_score

        r_off = analyze_and_score(test_audio, mode='quick', feature_flags=FeatureFlags())
        r_on = analyze_and_score(
            test_audio, mode='quick',
            feature_flags=FeatureFlags(
                enable_multiscale_hnr=True, enable_praat_cpp=True
            )
        )

        if not r_off.get('is_voice'):
            pytest.skip("Audio not detected as voice")

        tech_off = r_off.get('scores', {}).get('technique', 0)
        tech_on = r_on.get('scores', {}).get('technique', 0)
        diff = abs(tech_on - tech_off)
        assert diff > 0.5, \
            f"Technique: old={tech_off:.1f} new={tech_on:.1f} diff={diff:.1f}"

    def test_flags_on_scores_in_valid_range(self, test_audio):
        """flag 开启后所有分数在 [0,100] + Technique 变化"""
        if not test_audio:
            pytest.skip("melody.wav not found")
        from api.business.audio_analysis import analyze_and_score

        r_off = analyze_and_score(test_audio, mode='quick', feature_flags=FeatureFlags())
        r_on = analyze_and_score(
            test_audio, mode='quick',
            feature_flags=FeatureFlags(
                enable_multiscale_hnr=True, enable_praat_cpp=True,
                enable_voicing_detection=True
            )
        )

        if not r_off.get('is_voice'):
            pytest.skip("Audio not detected as voice")

        s_on, s_off = r_on.get('scores', {}), r_off.get('scores', {})
        for dim in ['pitch', 'rhythm', 'breath', 'technique', 'artistry']:
            val = s_on.get(dim, -1)
            assert 0 <= val <= 100, f"{dim}={val} not in [0,100]"

        tech_diff = abs(s_on.get('technique', 0) - s_off.get('technique', 0))
        assert tech_diff > 0.5, \
            f"Technique: old={s_off.get('technique',0):.1f} new={s_on.get('technique',0):.1f}"


class TestVoicingDetectionIntegration:

    def test_voicing_flag_produces_diagnostic_field(self):
        """enable_voicing_detection=True 时结果应有 _voicing_detection 字段"""
        from services.audio_features_service import AudioFeaturesService

        sr = 22050
        t = np.linspace(0, 1, sr, endpoint=False)
        signal = np.sin(2 * np.pi * 440 * t) * 0.5

        service = AudioFeaturesService(sample_rate=sr)
        result = service.extract_all_features(
            signal,
            feature_flags=FeatureFlags(enable_voicing_detection=True)
        )

        assert hasattr(result, '_voicing_detection'), "missing _voicing_detection"
        vd = result._voicing_detection
        assert vd is not None, "_voicing_detection is None"
        assert hasattr(vd, 'detection_confidence'), "missing detection_confidence"
        assert vd.detection_confidence > 0, \
            f"confidence={vd.detection_confidence}, expected > 0"
