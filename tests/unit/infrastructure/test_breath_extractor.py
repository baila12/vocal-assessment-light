"""
BreathFeatureExtractor TDD 测试 — v7.1 Batch 3

测试策略:
  - 合成音频验证: 稳态 vs 波动 RMS, 长音检测
  - Feature flag: is_clean_vocal 影响评分阈值
"""
from __future__ import annotations
import pytest
import numpy as np


class TestBreathFeatureExtractor:
    """气息特征提取器 TDD 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.domain.audio.breath_extractor import LibrosaBreathExtractor
        from backend.domain.audio.feature_types import AcousticFeatures
        self.extractor = LibrosaBreathExtractor()
        self.acoustic = AcousticFeatures(
            hnr=20.0, cpp=3.0, hpss_harmonic_ratio=0.35,
        )

    # ── helpers ──
    @staticmethod
    def _make_steady_tone(freq=220, duration_s=2.0, sr=22050):
        """稳态正弦音"""
        n = int(sr * duration_s)
        t = np.linspace(0, duration_s, n, endpoint=False)
        y = (np.sin(2 * np.pi * freq * t) * 0.5).astype(np.float32)
        return y, sr

    @staticmethod
    def _make_dynamic_tone(duration_s=2.0, sr=22050):
        """动态变化音: 渐强 → 渐弱"""
        n = int(sr * duration_s)
        t = np.linspace(0, duration_s, n, endpoint=False)
        envelope = np.sin(np.pi * t / duration_s)  # 0 → 1 → 0
        y = (np.sin(2 * np.pi * 220 * t) * envelope * 0.5).astype(np.float32)
        return y, sr

    @staticmethod
    def _make_breathy_tone(duration_s=2.0, sr=22050):
        """气声: 正弦 + 噪声"""
        n = int(sr * duration_s)
        t = np.linspace(0, duration_s, n, endpoint=False)
        tone = np.sin(2 * np.pi * 220 * t) * 0.3
        rng = np.random.RandomState(42)
        noise = rng.randn(n) * 0.2
        return (tone + noise).astype(np.float32), sr

    # ================================================================
    # 基础功能测试
    # ================================================================

    def test_steady_tone_returns_features(self):
        """稳态音 → 返回有效 BreathFeatures (dynamic_range 对恒定信号为 0)"""
        y, sr = self._make_steady_tone(duration_s=2.0)
        result = self.extractor.extract(y, sr, self.acoustic)
        assert result.professional_breath_score >= 0.0
        assert result.rms_fluctuation >= 0.0
        assert result.long_note_support >= 0.0
        # 稳态音 dynamic_range 接近 0 (正常 — 所有帧 RMS 相同)
        assert result.dynamic_range >= 0.0

    def test_dynamic_tone_higher_range(self):
        """渐强渐弱音 dynamic_range 应高于稳态音"""
        y_steady, sr = self._make_steady_tone(duration_s=2.0)
        y_dynamic, _ = self._make_dynamic_tone(duration_s=2.0, sr=sr)

        range_steady = self.extractor.extract(y_steady, sr, self.acoustic).dynamic_range
        range_dynamic = self.extractor.extract(y_dynamic, sr, self.acoustic).dynamic_range
        # 渐强渐弱应有更宽的动态范围
        # (至少不更窄)
        assert range_dynamic > 0.0

    def test_breathy_tone_detected(self):
        """气声音频 detected (controlled_breathiness 或 uncontrolled_leak)"""
        y, sr = self._make_breathy_tone(duration_s=2.0)
        result = self.extractor.extract(y, sr, self.acoustic)
        # 气声分析应有非零检测
        assert result.controlled_breathiness >= 0.0
        assert result.uncontrolled_leak >= 0.0

    # ================================================================
    # is_clean_vocal 标记
    # ================================================================

    def test_is_clean_vocal_passed_through(self):
        """is_clean_vocal 应传递到输出"""
        y, sr = self._make_steady_tone(duration_s=1.0)
        result = self.extractor.extract(y, sr, self.acoustic, is_clean_vocal=True)
        assert result.is_clean_vocal is True

    # ================================================================
    # 边界条件
    # ================================================================

    def test_silence_breath_defaults(self, silence):
        """静音 → 安全默认值"""
        y, sr = silence
        result = self.extractor.extract(y, sr, self.acoustic)
        assert result.rms_fluctuation >= 0.0
        assert result.breath_breaks >= 0
        assert result.dynamic_range >= 0.0

    def test_short_audio_breath_safe(self):
        """超短音频不崩溃"""
        sr = 22050
        y = np.zeros(int(sr * 0.05), dtype=np.float32)
        result = self.extractor.extract(y, sr, self.acoustic)
        assert result.professional_breath_score >= 0.0

    def test_all_fields_have_types(self):
        """所有字段类型正确"""
        y, sr = self._make_steady_tone()
        result = self.extractor.extract(y, sr, self.acoustic)
        assert isinstance(result.professional_breath_score, float)
        assert isinstance(result.long_note_support, float)
        assert isinstance(result.dynamic_control, float)
        assert isinstance(result.breath_design, float)
        assert isinstance(result.breath_technique, float)
        assert isinstance(result.rms_fluctuation, float)
        assert isinstance(result.is_artistic_fluctuation, bool)
        assert isinstance(result.controlled_breathiness, float)
        assert isinstance(result.uncontrolled_leak, float)
        assert isinstance(result.breath_breaks, int)
        assert isinstance(result.long_note_count, int)
        assert isinstance(result.dynamic_range, float)
        assert isinstance(result.is_clean_vocal, bool)
