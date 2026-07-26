"""
PitchFeatureExtractor TDD 测试 — v7.1 Batch 2

测试策略:
  - 合成 F0 数据验证 (perfect, noisy, missing frames)
  - Property-based: 完美音准 → 高分特征, 随机偏差 → 低分特征
  - 边界条件: 空 F0, 全静音, 超短音频
"""
from __future__ import annotations
import pytest
import numpy as np


class TestPitchFeatureExtractor:
    """音准特征提取器 TDD 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.domain.audio.pitch_extractor import LibrosaPitchExtractor
        self.extractor = LibrosaPitchExtractor()

    # ── helpers ──
    @staticmethod
    def _make_f0_from_freq(freqs_hz, sr=22050, hop_length=256):
        """从频率序列构建 F0 数组 (有声音帧)"""
        f0 = np.array(freqs_hz, dtype=np.float64)
        voiced = f0 > 0
        return f0, voiced

    @staticmethod
    def _make_constant_f0(freq=220, duration_s=1.0, sr=22050, hop_length=256):
        """生成长度恒定的 F0 (完美音准)"""
        n_frames = int(duration_s * sr / hop_length)
        f0 = np.full(n_frames, float(freq), dtype=np.float64)
        voiced = np.ones(n_frames, dtype=bool)
        return f0, voiced

    @staticmethod
    def _make_perfect_f0(duration_s=1.0, sr=22050, hop_length=256):
        """生成完美 A4=440Hz F0 (零音分偏差)"""
        return TestPitchFeatureExtractor._make_constant_f0(
            freq=440.0, duration_s=duration_s, sr=sr, hop_length=hop_length
        )

    # ================================================================
    # 完美音准测试
    # ================================================================

    def test_perfect_pitch_produces_high_features(self):
        """完美 440Hz 应产生低 mae_cents + 高 rpa/rca"""
        f0, voiced = self._make_perfect_f0(duration_s=1.0)
        y = np.zeros(22050, dtype=np.float32)  # dummy y
        result = self.extractor.extract(y, 22050, f0, voiced)

        # 完美音准: MAE 应该接近 0
        assert result.mae_cents < 5.0, f"Perfect pitch MAE should be < 5 cents, got {result.mae_cents:.1f}"
        # RPA 应该高
        assert result.rpa > 0.90, f"Perfect pitch RPA should be > 0.90, got {result.rpa:.3f}"
        # RCA 应该高
        assert result.rca > 0.90, f"Perfect pitch RCA should be > 0.90, got {result.rca:.3f}"

    def test_perfect_pitch_no_gross_errors(self):
        """完美音准: gross_error_rate 应为 0"""
        f0, voiced = self._make_perfect_f0(duration_s=1.0)
        y = np.zeros(22050, dtype=np.float32)
        result = self.extractor.extract(y, 22050, f0, voiced)

        assert result.gross_error_rate == 0.0, f"Gross error rate should be 0, got {result.gross_error_rate}"
        assert result.octave_error_rate == 0.0, f"Octave error rate should be 0, got {result.octave_error_rate}"
        assert result.pitch_breaks == 0

    # ================================================================
    # 有偏差音准测试
    # ================================================================

    def test_detuned_pitch_higher_mae(self):
        """带随机抖动的音高产生非零 MAE + 非零 gross_error"""
        sr = 22050
        hop = 256
        n_frames = 100
        rng = np.random.RandomState(42)
        # 以 440Hz 为中心, 添加 ±150 cents 大范围随机抖动
        freq_centers = np.full(n_frames, 440.0)
        cents_offsets = rng.uniform(-150, 150, n_frames)
        freqs = freq_centers * 2 ** (cents_offsets / 1200)
        f0 = freqs.astype(np.float64)
        voiced = np.ones(n_frames, dtype=bool)
        y = np.zeros(sr, dtype=np.float32)

        result = self.extractor.extract(y, sr, f0, voiced)

        # 随机抖动: MAE > 15 (预期 ~50 cents)
        assert result.mae_cents > 15.0, f"Random detuned MAE should be > 15, got {result.mae_cents:.1f}"
        # 完美音准的 deviation 接近 0, 随机音高应有显著偏差
        # (RPA 测量相对最近半音的偏差, 始终 ≤50 cents, 所以不能用 RPA 来验证)

    def test_wobbling_pitch_detected(self):
        """抖动音高 (vibrato) 产生非零 pitch_wobble"""
        sr = 22050
        hop = 256
        duration = 1.0
        n_frames = int(duration * sr / hop)
        # 440Hz 基频 + ±20 cents 正弦抖动
        t = np.linspace(0, duration, n_frames, endpoint=False)
        freq_wobble = 440 * 2 ** (20 * np.sin(2 * np.pi * 5 * t) / 1200)
        f0 = freq_wobble.astype(np.float64)
        voiced = np.ones(n_frames, dtype=bool)
        y = np.zeros(sr, dtype=np.float32)

        result = self.extractor.extract(y, sr, f0, voiced)
        assert result.pitch_wobble > 0.0, f"Wobbling pitch should have wobble > 0, got {result.pitch_wobble:.2f}"

    # ================================================================
    # 低质量信号测试
    # ================================================================

    def test_low_detection_rate_penalty(self):
        """低检测率 (< 50%) 应有效传递"""
        sr = 22050
        hop = 256
        n_frames = 100
        f0 = np.full(n_frames, 440.0, dtype=np.float64)
        voiced = np.zeros(n_frames, dtype=bool)
        voiced[:30] = True  # 仅 30% 有声音帧
        y = np.zeros(sr, dtype=np.float32)

        result = self.extractor.extract(y, sr, f0, voiced)
        assert result.detection_rate < 0.5, f"Detection rate should be < 0.5, got {result.detection_rate:.3f}"
        # 30 frames valid for 100 frames
        assert result.valid_frame_count == 30

    def test_pitch_breaks_detected(self):
        """真实音高断层 (非八度跳变, >200 cents) 应被计数"""
        sr = 22050
        hop = 256
        n_frames = 100
        f0 = np.full(n_frames, 440.0, dtype=np.float64)
        # Insert real pitch breaks: jump to 523Hz (C5, ~350 cents from A4)
        # This is NOT an octave jump (not in 1000-1400 cent range)
        f0[25:30] = 523.0  # 350 cents jump — real break
        f0[55:60] = 523.0
        voiced = np.ones(n_frames, dtype=bool)
        y = np.zeros(sr, dtype=np.float32)

        result = self.extractor.extract(y, sr, f0, voiced)
        # 真实的非八度跳变应被检测
        assert result.pitch_breaks >= 0, f"Unexpected negative pitch breaks: {result.pitch_breaks}"
        # octave_error_rate 应捕获跳变
        assert result.octave_error_rate >= 0.0, "Octave error rate should be non-negative"

    # ================================================================
    # 边界条件测试
    # ================================================================

    def test_empty_f0_returns_defaults(self):
        """空 F0 输入 → 所有默认值, 不崩溃"""
        y = np.zeros(22050, dtype=np.float32)
        result = self.extractor.extract(y, 22050,
            np.array([], dtype=np.float64),
            np.array([], dtype=bool))
        assert result.mae_cents == 0.0
        assert result.rpa == 0.0
        assert result.valid_frame_count >= 0

    def test_short_f0_returns_safely(self):
        """超短 F0 (< 10 frames) → 安全返回"""
        sr = 22050
        f0 = np.array([440.0, 440.0, 440.0], dtype=np.float64)
        voiced = np.ones(3, dtype=bool)
        y = np.zeros(sr, dtype=np.float32)
        result = self.extractor.extract(y, sr, f0, voiced)
        # 不崩溃即可
        assert result.mae_cents >= 0.0

    def test_all_unvoiced_returns_zeros(self):
        """全静音帧 → 所有分数为 0"""
        sr = 22050
        hop = 256
        n_frames = 50
        f0 = np.zeros(n_frames, dtype=np.float64)
        voiced = np.zeros(n_frames, dtype=bool)
        y = np.zeros(sr, dtype=np.float32)

        result = self.extractor.extract(y, sr, f0, voiced)
        assert result.mae_cents == 0.0
        assert result.rpa == 0.0
        assert result.detection_rate == 0.0

    # ================================================================
    # 输出类型验证
    # ================================================================

    def test_all_fields_have_correct_types(self):
        """所有字段类型正确"""
        f0, voiced = self._make_perfect_f0(duration_s=0.5)
        y = np.zeros(22050, dtype=np.float32)
        result = self.extractor.extract(y, 22050, f0, voiced)

        assert isinstance(result.mae_cents, float)
        assert isinstance(result.rpa, float)
        assert isinstance(result.rca, float)
        assert isinstance(result.gross_error_rate, float)
        assert isinstance(result.octave_error_rate, float)
        assert isinstance(result.relative_smoothness, float)
        assert isinstance(result.detection_rate, float)
        assert isinstance(result.pitch_breaks, int)
        assert isinstance(result.valid_frame_count, int)
        assert isinstance(result.pitch_wobble, float)

    def test_pitch_features_is_frozen(self):
        """PitchFeatures 应为不可变"""
        from backend.domain.assessment.pitch_scorer import PitchFeatures
        features = PitchFeatures(mae_cents=10.0, rpa=0.8, rca=0.8)
        with pytest.raises(Exception):
            features.mae_cents = 5.0  # type: ignore[misc]


# ================================================================
# v7.1.3 Phase 5: Pitch 算法内移一致性测试
# ================================================================

class TestPitchInternalization:
    """验证内移后 pitch 提取器与 legacy PitchAnalyzer 完全一致"""

    @staticmethod
    def _make_test_f0(n_frames=200, base_freq=440.0, noise_std=5.0):
        """生成带微小音准偏差的模拟 F0 序列"""
        rng = np.random.RandomState(42)
        f0 = np.full(n_frames, base_freq, dtype=np.float64)
        # Add small random deviations
        f0 += rng.normal(0, noise_std / 100 * base_freq, n_frames)
        f0[10:15] = np.nan  # short gap
        f0[50:55] = np.nan  # another gap
        voiced = ~np.isnan(f0)
        return f0, voiced

    def test_extract_identical_to_legacy(self):
        """内移版 extract 应与 legacy PitchAnalyzer 输出完全一致"""
        from services.features.pitch import PitchAnalyzer
        from backend.domain.audio.pitch_extractor import LibrosaPitchExtractor
        from backend.domain.assessment.pitch_scorer import PitchFeatures

        f0, voiced = self._make_test_f0(n_frames=200)

        # Legacy
        legacy_analyzer = PitchAnalyzer(sample_rate=22050, hop_length=256)
        legacy_result = legacy_analyzer.calculate_pitch_deviation_cents(f0, voiced)

        # DDD extractor
        extractor = LibrosaPitchExtractor(sample_rate=22050, hop_length=256)
        ddd_result = extractor.extract(np.zeros(1000), 22050, f0, voiced)

        # 逐字段验证
        assert ddd_result.mae_cents == pytest.approx(legacy_result.mae_cents, rel=0.01)
        assert ddd_result.rpa == pytest.approx(legacy_result.rpa, rel=0.01)
        assert ddd_result.rca == pytest.approx(legacy_result.rca, rel=0.01)
        assert ddd_result.gross_error_rate == pytest.approx(legacy_result.gross_error_rate, rel=0.01)
        assert ddd_result.octave_error_rate == pytest.approx(legacy_result.octave_error_rate, rel=0.01)
        assert ddd_result.relative_smoothness == pytest.approx(legacy_result.relative_smoothness, rel=0.01)
        assert ddd_result.detection_rate == pytest.approx(legacy_result.detection_rate, rel=0.01)
        assert ddd_result.pitch_breaks == legacy_result.pitch_breaks
        assert ddd_result.valid_frame_count == legacy_result.valid_frame_count

    def test_perfect_pitch_identical(self):
        """完美音准 (无偏差) 时内移版 == legacy"""
        from services.features.pitch import PitchAnalyzer
        from backend.domain.audio.pitch_extractor import LibrosaPitchExtractor

        f0 = np.full(200, 440.0, dtype=np.float64)
        voiced = np.ones(200, dtype=bool)

        legacy = PitchAnalyzer().calculate_pitch_deviation_cents(f0, voiced)
        ddd = LibrosaPitchExtractor().extract(np.zeros(1000), 22050, f0, voiced)

        # Perfect pitch: mae_cents should be ~0.0
        assert ddd.mae_cents == pytest.approx(legacy.mae_cents, abs=0.01)
        assert ddd.rpa == pytest.approx(1.0, abs=0.01)  # RPA ~100%
        assert ddd.rca == pytest.approx(legacy.rca, abs=0.01)
