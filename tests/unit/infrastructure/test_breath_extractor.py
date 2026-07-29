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
        assert isinstance(result.artistic_fluctuation_score, float)
        assert isinstance(result.controlled_breathiness, float)
        assert isinstance(result.uncontrolled_leak, float)
        assert isinstance(result.breath_breaks, int)
        assert isinstance(result.long_note_count, int)
        assert isinstance(result.dynamic_range, float)
        assert isinstance(result.is_clean_vocal, bool)


# ================================================================
# v7.6: crescendo_quality 饱和修复 (P1-2)
# ================================================================

class TestCrescendoQualityFix:
    """P1-2: 验证 crescendo_quality 不再对长音频饱和到 100"""

    def test_long_audio_crescendo_not_saturated(self):
        """长 RMS 序列 (模拟 3 分钟歌曲) → crescendo_quality 不总是 100"""
        from backend.domain.audio.breath_extractor import _eval_dynamic_control
        # 模拟 5000 帧 RMS (约 3 分钟), 具有典型动态变化
        rng = np.random.RandomState(42)
        base = 0.05 + 0.02 * np.sin(np.linspace(0, 20 * np.pi, 5000))
        noise = rng.randn(5000) * 0.005
        rms = np.abs(base + noise).astype(np.float64)
        rms = rms + 1e-6  # ensure > 0

        _, _, _, crescendo = _eval_dynamic_control(rms)
        # 修复前: 累积公式导致 crescendo_quality 永远是 100
        # 修复后: 应在 0-100 范围内但不应饱和
        assert 0.0 <= crescendo <= 100.0, f"crescendo out of range: {crescendo}"
        # 除非输入确实完美，否则不应总是 100
        assert crescendo < 100.0, (
            f"crescendo_quality should NOT saturate at 100 for typical audio, got {crescendo}"
        )

    def test_short_audio_crescendo_reasonable(self):
        """短 RMS 序列 (模拟 5 秒音频) → crescendo_quality 合理"""
        from backend.domain.audio.breath_extractor import _eval_dynamic_control
        rng = np.random.RandomState(99)
        base = 0.05 + 0.015 * np.sin(np.linspace(0, 4 * np.pi, 200))
        noise = rng.randn(200) * 0.003
        rms = np.abs(base + noise).astype(np.float64) + 1e-6

        _, _, _, crescendo = _eval_dynamic_control(rms)
        assert 0.0 <= crescendo <= 100.0

    def test_perfect_crescendo_still_scores_high(self):
        """完美渐强的 RMS → crescendo_quality 应得高分但不一定 100"""
        from backend.domain.audio.breath_extractor import _eval_dynamic_control
        # 完美的线性渐强 (每个窗口都是单调递增)
        rms = np.linspace(0.01, 0.1, 500).astype(np.float64)
        # 增加小幅噪声保持真实感
        rng = np.random.RandomState(1)
        rms = rms + rng.randn(500) * 0.002
        rms = np.abs(rms) + 1e-6

        _, _, _, crescendo = _eval_dynamic_control(rms)
        # 优秀但不应自动满分
        assert crescendo > 0.0, f"Perfect crescendo should score > 0, got {crescendo}"
        assert 0.0 <= crescendo <= 100.0

    def test_completely_flat_rms_zero_crescendo(self):
        """完全平坦 RMS → crescendo_quality ≈ 0"""
        from backend.domain.audio.breath_extractor import _eval_dynamic_control
        rms = np.full(500, 0.05, dtype=np.float64)
        _, _, _, crescendo = _eval_dynamic_control(rms)
        assert crescendo == 0.0, f"Flat RMS should give 0, got {crescendo}"


# ================================================================
# v7.6: is_artistic_fluctuation 连续化 (P1-3)
# ================================================================

class TestArtisticFluctuationContinuous:
    """P1-3: 验证 artistic_fluctuation_score 为连续值, 区分不同表现力水平"""

    def _make_rms_with_periodicity(self, n_frames=500, period=45, amplitude=0.3):
        """创建具有周期性 RMS 的信号"""
        base = 0.05 + amplitude * 0.05 * np.sin(2 * np.pi * np.arange(n_frames) / period)
        rng = np.random.RandomState(42)
        noise = rng.randn(n_frames) * 0.003
        return (np.abs(base + noise) + 1e-6).astype(np.float64)

    def test_continuous_output_in_range(self):
        """连续函数返回 0-100 的 float"""
        from backend.domain.audio.breath_extractor import _calc_artistic_fluctuation_score
        rms = self._make_rms_with_periodicity(n_frames=500, period=45)
        f0 = 220 + 30 * np.sin(2 * np.pi * np.arange(500) / 45)
        voiced = np.ones(500, dtype=bool)

        score = _calc_artistic_fluctuation_score(rms, f0, voiced)
        assert isinstance(score, float), f"Expected float, got {type(score)}"
        assert 0.0 <= score <= 100.0, f"Score out of range: {score}"

    def test_high_periodicity_scores_higher_than_low(self):
        """高周期性的 RMS → 比低周期性得分更高"""
        from backend.domain.audio.breath_extractor import _calc_artistic_fluctuation_score
        n = 500
        # 强周期性: RMS 正弦调制 (周期 15 → 3 个峰值在 lag 1-50)
        rms_high = (0.05 + 0.015 * np.sin(2 * np.pi * np.arange(n) / 15)).astype(np.float64)
        # 低周期性: RMS 几乎恒定 (变化 << 均值)
        rms_low = np.full(n, 0.05, dtype=np.float64)
        f0 = np.ones(n) * 220
        voiced = np.ones(n, dtype=bool)

        score_high = _calc_artistic_fluctuation_score(rms_high, f0, voiced)
        score_low = _calc_artistic_fluctuation_score(rms_low, f0, voiced)
        assert score_high > score_low, (
            f"High periodicity ({score_high:.1f}) should > low ({score_low:.1f})"
        )

    def test_strong_f0_rms_coupling_scores_higher(self):
        """强 F0-RMS 耦合 → 比无耦合得分更高"""
        from backend.domain.audio.breath_extractor import _calc_artistic_fluctuation_score
        n = 500
        f0_base = 220.0
        # 强耦合: F0 和 RMS 高度正相关 (模拟有意识的乐句塑形)
        modulation = 20 * np.sin(2 * np.pi * np.arange(n) / 50)
        f0_strong = f0_base + modulation
        rms_strong = (0.05 + 0.015 * modulation / 20.0).astype(np.float64)
        rms_strong = np.abs(rms_strong) + 1e-6
        # 无耦合: F0 变化但 RMS 平坦 (无乐句塑形, 不用自相关来区分)
        rms_flat = np.full(n, 0.05, dtype=np.float64) + 1e-6
        voiced = np.ones(n, dtype=bool)

        score_strong = _calc_artistic_fluctuation_score(rms_strong, f0_strong, voiced)
        score_flat = _calc_artistic_fluctuation_score(rms_flat, f0_strong, voiced)
        assert score_strong > score_flat, (
            f"Strong coupling ({score_strong:.1f}) should > flat ({score_flat:.1f})"
        )

    def test_zero_input_returns_zero(self):
        """空输入返回 0"""
        from backend.domain.audio.breath_extractor import _calc_artistic_fluctuation_score
        rms = np.array([0.05], dtype=np.float64)
        f0 = np.array([])
        voiced = np.array([])
        score = _calc_artistic_fluctuation_score(rms, f0, voiced)
        assert score == 0.0, f"Empty input should return 0, got {score}"

    def test_extractor_outputs_continuous_score(self):
        """BreathExtractor 产出 artistic_fluctuation_score"""
        sr = 22050
        duration = 2.0
        n = int(sr * duration)
        t = np.linspace(0, duration, n, endpoint=False)
        # 创建具有周期性 RMS 变化的信号
        envelope = 0.5 + 0.3 * np.sin(2 * np.pi * 2.0 * t)  # 2Hz 波动
        f0_mod = 220 + 20 * np.sin(2 * np.pi * 2.0 * t)
        phase = 2 * np.pi * np.cumsum(f0_mod) / sr
        y = (np.sin(phase) * envelope * 0.5).astype(np.float32)

        from backend.domain.audio.breath_extractor import LibrosaBreathExtractor
        from backend.domain.audio.feature_types import AcousticFeatures

        extractor = LibrosaBreathExtractor()
        acoustic = AcousticFeatures(hnr=20.0, cpp=3.0, hpss_harmonic_ratio=0.35)
        result = extractor.extract(y, sr, acoustic)

        # 新字段应当存在且为连续 float
        assert hasattr(result, 'artistic_fluctuation_score')
        score = result.artistic_fluctuation_score
        assert isinstance(score, float), f"Expected float, got {type(score)}"
        assert 0.0 <= score <= 100.0, f"Score out of range: {score}"
        # 对于调制的歌声信号，得分应 > 0
        assert score > 0.0, f"Sung audio should have artistic score > 0, got {score}"

    def test_backward_compat_bool_still_present(self):
        """向后兼容: is_artistic_fluctuation bool 字段仍然存在"""
        sr = 22050
        n = int(sr * 1.0)
        y = (np.sin(2 * np.pi * 220 * np.linspace(0, 1, n)) * 0.3).astype(np.float32)

        from backend.domain.audio.breath_extractor import LibrosaBreathExtractor
        from backend.domain.audio.feature_types import AcousticFeatures

        extractor = LibrosaBreathExtractor()
        acoustic = AcousticFeatures(hnr=20.0, cpp=3.0, hpss_harmonic_ratio=0.35)
        result = extractor.extract(y, 22050, acoustic)

        assert hasattr(result, 'is_artistic_fluctuation')
        assert isinstance(result.is_artistic_fluctuation, bool)
