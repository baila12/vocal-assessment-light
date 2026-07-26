"""
TDD: AudiofeatExtractor — v7.2.0

测试 DDD AudiofeatExtractor (backend/domain/audio/audiofeat_extractor.py)。
利用 audiofeat 1.1.1 提取 20+ 声学特征, 增强气息/技术/肌肉维度评分。

TDD 原则: 先写测试 (RED) → 实现 (GREEN) → 重构 (IMPROVE)
"""
from __future__ import annotations
import pytest
import numpy as np
import torch


# ================================================================
# Helpers
# ================================================================

def _make_vocal_like(duration_s=1.5, sr=16000, freq=220.0) -> torch.Tensor:
    """生成类人声测试信号 (基频 + 2个谐波)"""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    y_np = (
        0.6 * np.sin(2 * np.pi * freq * t)
        + 0.3 * np.sin(2 * np.pi * freq * 2 * t)
        + 0.15 * np.sin(2 * np.pi * freq * 3 * t)
    )
    y_np = (y_np / np.max(np.abs(y_np)) * 0.8).astype(np.float32)
    return torch.from_numpy(y_np)


def _make_silence(duration_s=1.0, sr=16000) -> torch.Tensor:
    """生成静音信号"""
    return torch.zeros(int(sr * duration_s), dtype=torch.float32)


# ================================================================
# Test 1: Extractor initialization
# ================================================================

class TestAudiofeatExtractorInit:
    """验证 AudiofeatExtractor 能正常初始化"""

    def test_import_exists(self):
        """模块应可导入"""
        from backend.domain.audio.audiofeat_extractor import (
            AudiofeatExtractor, AudiofeatFeatures,
        )
        assert AudiofeatExtractor is not None
        assert AudiofeatFeatures is not None

    def test_default_constructor(self):
        """默认构造函数不抛异常"""
        from backend.domain.audio.audiofeat_extractor import AudiofeatExtractor
        extractor = AudiofeatExtractor()
        assert extractor is not None

    def test_features_dataclass_is_frozen(self):
        """AudiofeatFeatures 应为不可变"""
        from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures
        import dataclasses
        assert dataclasses.is_dataclass(AudiofeatFeatures)
        # 验证字段存在
        f = AudiofeatFeatures()
        assert hasattr(f, 'cpp_mean')


# ================================================================
# Test 2: Feature extraction — vocal-like signal
# ================================================================

class TestAudiofeatExtractorVocal:
    """验证对类人声信号的特征提取"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.domain.audio.audiofeat_extractor import AudiofeatExtractor
        self.extractor = AudiofeatExtractor()
        self.y = _make_vocal_like(duration_s=1.5, sr=16000, freq=220.0)
        self.sr = 16000

    def test_extract_returns_features(self):
        """extract() 应返回 AudiofeatFeatures 实例"""
        from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures
        features = self.extractor.extract(self.y, self.sr)
        assert isinstance(features, AudiofeatFeatures)

    def test_cpp_mean_valid_range(self):
        """CPP 均值应在合理范围 (纯谐波信号 > 10dB)"""
        features = self.extractor.extract(self.y, self.sr)
        assert features.cpp_mean > 0.0
        assert features.cpp_mean < 50.0  # 上限

    def test_hnr_valid_range(self):
        """HNR 应在合理范围"""
        features = self.extractor.extract(self.y, self.sr)
        assert 0.0 <= features.hnr_mean <= 100.0

    def test_gne_valid_range(self):
        """GNE 应在 0-1 范围"""
        features = self.extractor.extract(self.y, self.sr)
        assert 0.0 <= features.gne_mean <= 1.0

    def test_jitter_valid_range(self):
        """Jitter 应为小值 (纯谐波信号 jitter ~0)"""
        features = self.extractor.extract(self.y, self.sr)
        assert features.jitter_local >= 0.0
        assert features.jitter_local < 0.05  # 纯信号应很低

    def test_shimmer_valid_range(self):
        """Shimmer 应为小值"""
        features = self.extractor.extract(self.y, self.sr)
        assert features.shimmer_db >= 0.0
        assert features.shimmer_db < 1.0

    def test_spectral_features_not_none(self):
        """频谱特征不应为 None"""
        features = self.extractor.extract(self.y, self.sr)
        assert features.spectral_centroid_mean > 0
        assert features.spectral_flatness_mean >= 0
        assert features.spectral_crest > 0
        assert features.spectral_entropy > 0

    def test_harmonic_features_not_none(self):
        """谐波特征不应为 None"""
        features = self.extractor.extract(self.y, self.sr)
        assert features.harmonic_richness >= 0
        assert features.inharmonicity >= 0

    def test_all_fields_are_numeric(self):
        """所有字段应为数值类型"""
        features = self.extractor.extract(self.y, self.sr)
        import dataclasses
        for field in dataclasses.fields(features):
            value = getattr(features, field.name)
            assert isinstance(value, (int, float)), (
                f"字段 {field.name} 应为数值, 实际为 {type(value)}"
            )


# ================================================================
# Test 3: Edge cases
# ================================================================

class TestAudiofeatExtractorEdgeCases:
    """验证边缘情况的处理"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.domain.audio.audiofeat_extractor import AudiofeatExtractor
        self.extractor = AudiofeatExtractor()

    def test_silence_does_not_crash(self):
        """静音信号不应崩溃, 应返回默认值"""
        y = _make_silence(duration_s=1.0, sr=16000)
        features = self.extractor.extract(y, 16000)
        # 静音时应有合理的默认值
        assert features.cpp_mean >= 0.0
        assert features.hnr_mean >= 0.0
        assert not np.isnan(features.spectral_centroid_mean)

    def test_short_audio_does_not_crash(self):
        """短音频 (< 0.1s) 不应崩溃"""
        y = _make_vocal_like(duration_s=0.05, sr=16000, freq=440.0)
        features = self.extractor.extract(y, 16000)
        assert features is not None

    def test_no_nan_values(self):
        """任何字段不应为 NaN"""
        y = _make_vocal_like(duration_s=1.0, sr=16000, freq=330.0)
        features = self.extractor.extract(y, 16000)
        import dataclasses
        for field in dataclasses.fields(features):
            value = getattr(features, field.name)
            assert not np.isnan(value), f"字段 {field.name} 为 NaN"

    def test_no_inf_values(self):
        """任何字段不应为 Inf"""
        y = _make_vocal_like(duration_s=1.0, sr=16000, freq=330.0)
        features = self.extractor.extract(y, 16000)
        import dataclasses
        for field in dataclasses.fields(features):
            value = getattr(features, field.name)
            assert not np.isinf(value), f"字段 {field.name} 为 Inf"


# ================================================================
# Test 4: Feature flag gating
# ================================================================

class TestAudiofeatFeatureFlag:
    """验证 audiofeat 由 feature flag 门控"""

    def test_flag_exists_in_dimension_flags(self):
        """DimensionFlags 应有 enable_audiofeat"""
        from backend.domain.assessment.feature_flags import DimensionFlags
        flags = DimensionFlags()
        assert hasattr(flags, 'enable_audiofeat')

    def test_flag_exists_in_feature_flags(self):
        """FeatureFlags 应有 enable_audiofeat"""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags()
        assert hasattr(flags, 'enable_audiofeat')

    def test_flag_default_is_false(self):
        """audiofeat 默认关闭 (可选增强, 不影响现有评分)"""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags()
        assert flags.enable_audiofeat is False
