"""
RhythmFeatureExtractor TDD 测试 — v7.1 Batch 2

测试策略:
  - 合成音频验证 (规律脉冲 → 低 deviation, 随机 → 高 deviation)
  - Onset 检测: 密集 vs 稀疏 vs 无 onset
  - is_clean_vocal 标记传递
"""
from __future__ import annotations
import pytest
import numpy as np


class TestRhythmFeatureExtractor:
    """节奏特征提取器 TDD 测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.domain.audio.rhythm_extractor import LibrosaRhythmExtractor
        self.extractor = LibrosaRhythmExtractor()

    # ── helpers ──
    @staticmethod
    def _make_click_track(bpm=120, duration_s=2.0, sr=22050):
        """生成节拍器脉冲 (规律性最大)"""
        n_samples = int(sr * duration_s)
        y = np.zeros(n_samples, dtype=np.float32)
        beat_interval = int(sr * 60 / bpm)
        for i in range(0, n_samples, beat_interval):
            # Short click pulse
            end = min(i + 50, n_samples)
            y[i:end] = 0.8 * np.hanning(end - i)
        return y, sr

    @staticmethod
    def _make_random_onset_audio(duration_s=2.0, sr=22050):
        """生成随机脉冲 (规律性最小)"""
        n_samples = int(sr * duration_s)
        y = np.zeros(n_samples, dtype=np.float32)
        rng = np.random.RandomState(42)
        n_clicks = 20
        positions = rng.choice(n_samples - 100, n_clicks, replace=False)
        for pos in positions:
            y[pos:pos + 50] = 0.5 * np.hanning(50)
        return y, sr

    @staticmethod
    def _make_no_onset_audio(duration_s=1.0, sr=22050):
        """静音 — 无 detectable onsets"""
        return np.zeros(int(sr * duration_s), dtype=np.float32), sr

    # ================================================================
    # 规律性测试
    # ================================================================

    def test_click_track_low_deviation(self):
        """节拍器: deviation_ratio 应低 (高规律性)"""
        y, sr = self._make_click_track(bpm=120, duration_s=2.0)
        result = self.extractor.extract(y, sr)

        # 规律脉冲 → 低偏差
        assert result.avg_deviation_ratio < 0.30, (
            f"Click track deviation should be < 0.30, got {result.avg_deviation_ratio:.3f}"
        )
        # 低不规律性
        assert result.irregularity < 0.30, (
            f"Click track irregularity should be < 0.30, got {result.irregularity:.3f}"
        )

    def test_random_onset_high_deviation(self):
        """随机脉冲: deviation_ratio 应高于节拍器"""
        y_click, sr = self._make_click_track(bpm=120, duration_s=2.0)
        y_random, _ = self._make_random_onset_audio(duration_s=2.0, sr=sr)

        click_dev = self.extractor.extract(y_click, sr).avg_deviation_ratio
        random_dev = self.extractor.extract(y_random, sr).avg_deviation_ratio

        assert random_dev > click_dev * 1.2, (
            f"Random deviation ({random_dev:.3f}) should be > 1.2× click deviation ({click_dev:.3f})"
        )

    # ================================================================
    # Onset 计数测试
    # ================================================================

    def test_click_track_onset_count(self):
        """节拍器: onset_count 应 > 0"""
        y, sr = self._make_click_track(bpm=120, duration_s=2.0)
        result = self.extractor.extract(y, sr)
        # 120 BPM × 2s = 4 beats, should detect some onsets
        assert result.onset_count > 0, f"Should detect onsets, got {result.onset_count}"
        assert result.onset_density > 0.0, f"Onset density should be > 0, got {result.onset_density}"

    def test_no_onset_audio(self):
        """静音: 无 detectable onsets"""
        y, sr = self._make_no_onset_audio(duration_s=1.0)
        result = self.extractor.extract(y, sr)
        # 静音不应检测到大量 onset
        assert result.onset_count < 10, f"Silence should have few onsets, got {result.onset_count}"

    # ================================================================
    # is_clean_vocal 标记
    # ================================================================

    def test_is_clean_vocal_false_by_default(self):
        """默认 is_clean_vocal=False"""
        y, sr = self._make_click_track(bpm=120, duration_s=1.0)
        result = self.extractor.extract(y, sr)
        assert result.is_clean_vocal is False

    def test_is_clean_vocal_true_passed_through(self):
        """is_clean_vocal=True 应传递到输出"""
        y, sr = self._make_click_track(bpm=120, duration_s=1.0)
        result = self.extractor.extract(y, sr, is_clean_vocal=True)
        assert result.is_clean_vocal is True

    # ================================================================
    # 边界条件
    # ================================================================

    def test_silence_rhythm_defaults(self, silence):
        """静音: 返回安全默认值, 不崩溃"""
        y, sr = silence
        result = self.extractor.extract(y, sr)
        assert result.avg_deviation_ratio >= 0.0
        assert result.onset_count >= 0
        assert result.onset_density >= 0.0

    def test_short_audio_rhythm_safe(self):
        """超短音频 (< 0.1s) 不崩溃"""
        sr = 22050
        y = np.zeros(int(sr * 0.05), dtype=np.float32)
        result = self.extractor.extract(y, sr)
        assert result.onset_count >= 0

    def test_all_fields_have_correct_types(self):
        """所有字段类型正确"""
        y, sr = self._make_click_track(bpm=120, duration_s=1.0)
        result = self.extractor.extract(y, sr)

        assert isinstance(result.avg_deviation_ratio, float)
        assert isinstance(result.irregularity, float)
        assert isinstance(result.onset_density, float)
        assert isinstance(result.onset_count, int)
        assert isinstance(result.off_beat_segments, int)
        assert isinstance(result.is_clean_vocal, bool)

    def test_rhythm_features_is_frozen(self):
        """RhythmFeatures 应为不可变"""
        from backend.domain.assessment.rhythm_scorer import RhythmFeatures
        features = RhythmFeatures(avg_deviation_ratio=0.1)
        with pytest.raises(Exception):
            features.avg_deviation_ratio = 0.5  # type: ignore[misc]


# ================================================================
# v7.1.3 Phase 6: Rhythm 算法内移一致性测试
# ================================================================

class TestRhythmInternalization:
    """验证 DDD rhythm 提取器行为 (v7.1.5 — legacy 对比已移除)"""

    @staticmethod
    def _make_rhythmic_audio(duration_s=3.0, sr=22050):
        """生成带节奏脉冲的测试音频"""
        rng = np.random.RandomState(42)
        n = int(sr * duration_s)
        y = rng.randn(n).astype(np.float32) * 0.02
        pulse_interval = int(sr / 2.0)
        for i in range(0, n, pulse_interval):
            pulse_len = min(int(sr * 0.05), n - i)
            t_pulse = np.linspace(0, np.pi, pulse_len)
            y[i:i+pulse_len] += (np.sin(t_pulse) * 0.8).astype(np.float32)
        return y / np.max(np.abs(y))

    def test_clean_vocal_flag_behavior(self):
        """is_clean_vocal 标记应正确传递并影响评分"""
        from backend.domain.audio.rhythm_extractor import LibrosaRhythmExtractor
        y = self._make_rhythmic_audio(duration_s=2.0)

        ddd_clean = LibrosaRhythmExtractor().extract(y, 22050, is_clean_vocal=True)
        ddd_mixed = LibrosaRhythmExtractor().extract(y, 22050, is_clean_vocal=False)

        assert ddd_clean.is_clean_vocal is True
        assert ddd_mixed.is_clean_vocal is False
        # Clean vocal vs mixed should produce different deviation ratios
        assert ddd_clean.avg_deviation_ratio != pytest.approx(
            ddd_mixed.avg_deviation_ratio, abs=0.001,
        ), "Clean vs mixed vocal should produce different deviation ratios"

    def test_rhythmic_audio_has_valid_onsets(self):
        """带节奏脉冲的音频应有可检测的 onset"""
        from backend.domain.audio.rhythm_extractor import LibrosaRhythmExtractor
        y = self._make_rhythmic_audio(duration_s=2.0)
        result = LibrosaRhythmExtractor().extract(y, 22050, is_clean_vocal=False)
        assert result.onset_count > 0, "Should detect onsets in rhythmic audio"
        assert result.onset_density > 0.0
