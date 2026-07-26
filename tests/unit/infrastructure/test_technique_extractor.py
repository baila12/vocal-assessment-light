"""
TechniqueFeatureExtractor TDD 测试 — v7.1 Batch 3

测试策略:
  - 合成音频验证: HNR→咬字, spectral_tilt→气声比
  - AcousticFeatures 消费者: 验证输入字段正确传递
"""
from __future__ import annotations
import pytest
import numpy as np


class TestTechniqueFeatureExtractor:
    """发声技术特征提取器 TDD 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.domain.audio.technique_extractor import LibrosaTechniqueExtractor
        from backend.domain.audio.feature_types import AcousticFeatures
        self.extractor = LibrosaTechniqueExtractor()
        # Good acoustic features
        self.acoustic = AcousticFeatures(
            hnr=25.0, cpp=4.0, spectral_tilt=-5.0,
            hpss_harmonic_ratio=0.40,
        )

    # ================================================================
    # HNR → 咬字清晰度
    # ================================================================

    def test_high_hnr_good_articulation(self):
        """高 HNR (25dB) → 高 consonant_clarity → 高 articulation"""
        y = np.zeros(22050, dtype=np.float32)
        result = self.extractor.extract(y, 22050, self.acoustic)

        # 高 HNR + 中等 CPP → 好的咬字潜力
        assert result.hnr_mean == 25.0, "HNR should be passed through"
        assert result.cpp_mean == 4.0, "CPP should be passed through"
        assert result.consonant_clarity > 0.0, "Consonant clarity should be computed"

    def test_low_hnr_reduced_clarity(self):
        """低 HNR → 低 consonant_clarity"""
        from backend.domain.audio.feature_types import AcousticFeatures
        low_acoustic = AcousticFeatures(hnr=5.0, cpp=1.0, spectral_tilt=-15.0)
        y = np.zeros(22050, dtype=np.float32)

        result_high = self.extractor.extract(y, 22050, self.acoustic)
        result_low = self.extractor.extract(y, 22050, low_acoustic)

        assert result_low.consonant_clarity < result_high.consonant_clarity, (
            f"Low HNR clarity ({result_low.consonant_clarity:.1f}) "
            f"should be < High HNR ({result_high.consonant_clarity:.1f})"
        )

    # ================================================================
    # Spectral Tilt → 气声比
    # ================================================================

    def test_negative_tilt_breathy(self):
        """负 spectral_tilt → 气声特征 (气声 > 压嗓)"""
        from backend.domain.audio.feature_types import AcousticFeatures
        breathy = AcousticFeatures(hnr=15.0, cpp=2.0, spectral_tilt=-15.0)  # 明显气声
        pressed = AcousticFeatures(hnr=25.0, cpp=5.0, spectral_tilt=+3.0)   # 压嗓

        y = np.zeros(22050, dtype=np.float32)
        r_breathy = self.extractor.extract(y, 22050, breathy)
        r_pressed = self.extractor.extract(y, 22050, pressed)

        # 负 tilt → hf_energy_ratio 较低 (更多低频能量)
        assert r_breathy.spectral_tilt < r_pressed.spectral_tilt, (
            f"Breathy tilt ({r_breathy.spectral_tilt}) should be < Pressed ({r_pressed.spectral_tilt})"
        )

    # ================================================================
    # Onset Density
    # ================================================================

    def test_pulse_audio_onset_density(self):
        """有脉冲的音频 → onset_density > 0"""
        sr = 22050
        duration = 1.0
        n = int(sr * duration)
        y = np.zeros(n, dtype=np.float32)
        # 添加脉冲
        for i in range(0, n, n // 10):
            end = min(i + 100, n)
            y[i:end] = 0.5 * np.hanning(end - i)

        result = self.extractor.extract(y, sr, self.acoustic)
        assert result.onset_density > 0.0, "Should detect onsets in pulse audio"

    # ================================================================
    # 边界条件
    # ================================================================

    def test_silence_technique_defaults(self, silence):
        """静音 → 安全默认值"""
        y, sr = silence
        result = self.extractor.extract(y, sr, self.acoustic)
        assert result.consonant_clarity >= 0.0
        assert result.hnr_mean == 25.0  # from acoustic
        assert result.spectral_tilt == -5.0  # from acoustic

    def test_all_fields_have_types(self):
        """所有字段类型正确"""
        y = np.zeros(22050, dtype=np.float32)
        result = self.extractor.extract(y, 22050, self.acoustic)

        assert isinstance(result.onset_density, float)
        assert isinstance(result.spectral_flux, float)
        assert isinstance(result.consonant_clarity, float)
        assert isinstance(result.hnr_mean, float)
        assert isinstance(result.spectral_tilt, float)
        assert isinstance(result.hf_energy_ratio, float)
        assert isinstance(result.cpp_mean, float)
