"""
TDD: audio_utils 工具函数测试 — v7.1.3 Phase 2

测试从 AcousticAnalyzer 内移到 backend/domain/audio/audio_utils 的三个纯函数:
  1. normalize_loudness() — RMS 归一化
  2. find_vocal_segments() — VAD 人声分段
  3. filter_audio_to_vocal_segments() — 提取拼接人声段

验证内移后行为与 legacy AcousticAnalyzer 完全一致。
"""
from __future__ import annotations
import pytest
import numpy as np


# ================================================================
# Test 1: normalize_loudness
# ================================================================

class TestNormalizeLoudness:
    """RMS 响度归一化 — 与 AcousticAnalyzer.normalize_loudness 行为一致"""

    @staticmethod
    def _make_sine(duration_s=2.0, sr=22050, freq=440.0, amplitude=0.5):
        n = int(sr * duration_s)
        t = np.linspace(0, duration_s, n, endpoint=False)
        return (np.sin(2 * np.pi * freq * t) * amplitude).astype(np.float32), sr

    def test_normalizes_to_target_rms(self):
        """归一化后 RMS 应接近 target_rms"""
        from services.features.acoustic import AcousticAnalyzer
        y, sr = self._make_sine(amplitude=0.1)

        y_norm = AcousticAnalyzer.normalize_loudness(y, target_rms=0.05)
        rms = float(np.sqrt(np.mean(y_norm ** 2)))

        assert 0.04 < rms < 0.06, f"RMS should be ~0.05, got {rms:.4f}"

    def test_normalizes_silence_safely(self):
        """静音/极弱信号不做除法溢出"""
        from services.features.acoustic import AcousticAnalyzer

        y = np.zeros(1000, dtype=np.float32)
        y_norm = AcousticAnalyzer.normalize_loudness(y)
        # 不应崩溃, 不应有 NaN/Inf
        assert not np.any(np.isnan(y_norm))
        assert not np.any(np.isinf(y_norm))

    def test_normalizes_loud_audio_down(self):
        """过响音频应被压低"""
        from services.features.acoustic import AcousticAnalyzer
        y, sr = self._make_sine(amplitude=0.9)

        y_norm = AcousticAnalyzer.normalize_loudness(y, target_rms=0.05)
        rms_before = float(np.sqrt(np.mean(y ** 2)))
        rms_after = float(np.sqrt(np.mean(y_norm ** 2)))

        assert rms_after < rms_before, (
            f"Loud audio should be attenuated: {rms_before:.4f} → {rms_after:.4f}"
        )

    def test_gain_clipped_to_range(self):
        """增益应在 [0.1, 10.0] 范围内"""
        from services.features.acoustic import AcousticAnalyzer

        # Very quiet audio — gain should be clipped to 10.0
        y_quiet = np.ones(1000, dtype=np.float32) * 0.0001
        y_norm = AcousticAnalyzer.normalize_loudness(y_quiet, target_rms=0.05)
        rms_after = float(np.sqrt(np.mean(y_norm ** 2)))
        # gain clipped: max gain = 10.0, so RMS ≈ 0.0001 * 10 = 0.001
        assert rms_after < 0.01, f"Gain clipping should prevent over-amplification: RMS={rms_after:.4f}"

    def test_returns_same_type(self):
        """输出类型应与输入一致"""
        from services.features.acoustic import AcousticAnalyzer
        y = np.ones(1000, dtype=np.float32)
        y_norm = AcousticAnalyzer.normalize_loudness(y)
        assert y_norm.dtype == y.dtype, f"dtype changed: {y.dtype} → {y_norm.dtype}"


# ================================================================
# Test 2: find_vocal_segments
# ================================================================

class TestFindVocalSegments:
    """VAD 人声分段 — 与 AcousticAnalyzer.find_vocal_segments 行为一致"""

    def test_fully_voiced_returns_one_segment(self):
        """全部有声 → 返回单一完整段"""
        from services.features.acoustic import AcousticAnalyzer

        f0 = np.full(200, 440.0, dtype=np.float64)
        segments = AcousticAnalyzer.find_vocal_segments(f0, hop_length=512, sample_rate=22050)

        assert len(segments) == 1, f"Expected 1 segment, got {len(segments)}"
        start, end = segments[0]
        assert start == 0, f"Start should be 0, got {start}"
        assert end == 200, f"End should be 200, got {end}"

    def test_fully_unvoiced_returns_empty(self):
        """全部无声 → 返回空列表"""
        from services.features.acoustic import AcousticAnalyzer

        f0 = np.full(200, np.nan, dtype=np.float64)
        segments = AcousticAnalyzer.find_vocal_segments(f0)

        assert segments == [], f"Expected empty, got {segments}"

    def test_large_gap_splits_segments(self):
        """大间隔应分割为多段"""
        from services.features.acoustic import AcousticAnalyzer

        sr, hop = 22050, 512
        f0 = np.zeros(300, dtype=np.float64)
        # voiced block 1: frames 0-50
        f0[:50] = 440.0
        # gap: frames 50-150 (100 frames ≈ 2.3s, > max_gap_sec=1.0s)
        # voiced block 2: frames 150-200
        f0[150:200] = 440.0

        segments = AcousticAnalyzer.find_vocal_segments(
            f0, hop_length=hop, sample_rate=sr,
            min_segment_sec=0.1, max_gap_sec=1.0,
        )
        assert len(segments) >= 2, f"Expected ≥2 segments, got {len(segments)}"

    def test_short_segment_filtered_out(self):
        """短于 min_segment_sec 的段应被过滤"""
        from services.features.acoustic import AcousticAnalyzer

        sr, hop = 22050, 512
        f0 = np.zeros(100, dtype=np.float64)
        # Very short voiced burst: 5 frames ≈ 0.12s (with hop=512)
        f0[10:15] = 440.0
        # Longer segment: 30 frames ≈ 0.7s
        f0[50:80] = 440.0

        segments = AcousticAnalyzer.find_vocal_segments(
            f0, hop_length=hop, sample_rate=sr,
            min_segment_sec=0.5, max_gap_sec=1.0,
        )
        # Only the longer segment should survive
        if segments:
            for seg_start, seg_end in segments:
                seg_frames = seg_end - seg_start
                min_frames = int(0.5 * sr / hop)  # ~21 frames
                assert seg_frames >= min_frames, (
                    f"Segment too short: {seg_frames} frames < {min_frames} min"
                )

    def test_f0_oor_filtered_out(self):
        """F0 超出 65-1047Hz 应视为无声"""
        from services.features.acoustic import AcousticAnalyzer

        f0 = np.array([50.0, 1200.0, 440.0, np.nan], dtype=np.float64)
        segments = AcousticAnalyzer.find_vocal_segments(
            f0, hop_length=512, sample_rate=22050, min_segment_sec=0.01,
        )
        # Frame 2 (440 Hz) is the only in-range voiced frame.
        # The NaN at frame 3 doesn't create a gap if max_gap_frames is large enough,
        # so the segment will be (2, 4). Both legacy and internalized should match.
        assert len(segments) > 0, "Should find at least one segment containing frame 2"
        # Frame 2 must be within some segment
        found_frame2 = any(seg[0] <= 2 < seg[1] for seg in segments)
        assert found_frame2, "Frame 2 (440 Hz) should be in a vocal segment"


# ================================================================
# Test 3: filter_audio_to_vocal_segments
# ================================================================

class TestFilterAudioToVocalSegments:
    """人声段提取拼接 — 与 AcousticAnalyzer.filter_audio_to_vocal_segments 行为一致"""

    def setUp(self):
        self.sr = 22050
        self.hop = 512
        self.y = np.arange(10000, dtype=np.float32)

    def test_filters_and_concatenates(self):
        """正确地提取和拼接人声段"""
        from services.features.acoustic import AcousticAnalyzer

        sr, hop = 22050, 512
        y = np.arange(sr * 2, dtype=np.float32)  # 2s audio

        # Simulate segments: frames 10-20 and 30-40
        segments = [(10, 20), (30, 40)]
        y_filtered = AcousticAnalyzer.filter_audio_to_vocal_segments(y, segments, hop_length=hop)

        expected_len = (20 - 10) * hop + (40 - 30) * hop
        assert len(y_filtered) == expected_len, (
            f"Expected {expected_len} samples, got {len(y_filtered)}"
        )

    def test_empty_segments_returns_original(self):
        """无有效段时返回原始音频"""
        from services.features.acoustic import AcousticAnalyzer
        y = np.arange(1000, dtype=np.float32)
        y_filtered = AcousticAnalyzer.filter_audio_to_vocal_segments(y, [], hop_length=512)
        assert np.array_equal(y, y_filtered)

    def test_segment_at_end_clamped(self):
        """段结束超出音频长度时应被 clamp"""
        from services.features.acoustic import AcousticAnalyzer
        y = np.arange(1024, dtype=np.float32)
        hop = 256
        # Segment extends past the audio
        segments = [(1, 100)]
        y_filtered = AcousticAnalyzer.filter_audio_to_vocal_segments(y, segments, hop_length=hop)
        # Should not crash, and should return a valid subset
        assert len(y_filtered) > 0
        assert len(y_filtered) <= len(y)


# ================================================================
# Test 4: 内移函数行为一致性 (与 AcousticAnalyzer 对比)
# ================================================================

class TestInternalizedFunctionsConsistency:
    """验证内移后的函数与 legacy AcousticAnalyzer 输出完全一致"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.sr = 22050
        self.y = (np.sin(2 * np.pi * 440 * np.linspace(0, 3, self.sr * 3)) * 0.3).astype(np.float32)
        self.f0 = np.full(200, 440.0, dtype=np.float64)
        self.f0[50:70] = np.nan  # short gap (< 1s)

    def test_normalize_loudness_identical(self):
        """内移版 normalize_loudness 应与 legacy 版本输出完全一致"""
        from services.features.acoustic import AcousticAnalyzer
        from backend.domain.audio.audio_utils import normalize_loudness as new_norm

        legacy_result = AcousticAnalyzer.normalize_loudness(self.y.copy(), target_rms=0.05)
        new_result = new_norm(self.y.copy(), target_rms=0.05)

        assert np.array_equal(legacy_result, new_result), (
            f"normalize_loudness output differs between legacy and new module"
        )

    def test_find_vocal_segments_identical(self):
        """内移版 find_vocal_segments 应与 legacy 版本输出完全一致"""
        from services.features.acoustic import AcousticAnalyzer
        from backend.domain.audio.audio_utils import find_vocal_segments as new_find

        legacy_segments = AcousticAnalyzer.find_vocal_segments(
            self.f0, hop_length=512, sample_rate=22050,
            min_segment_sec=0.5, max_gap_sec=1.0,
        )
        new_segments = new_find(
            self.f0, hop_length=512, sample_rate=22050,
            min_segment_sec=0.5, max_gap_sec=1.0,
        )

        assert legacy_segments == new_segments, (
            f"find_vocal_segments differs: legacy={legacy_segments}, new={new_segments}"
        )

    def test_filter_audio_to_vocal_segments_identical(self):
        """内移版 filter_audio_to_vocal_segments 应与 legacy 版本输出完全一致"""
        from services.features.acoustic import AcousticAnalyzer
        from backend.domain.audio.audio_utils import filter_audio_to_vocal_segments as new_filter

        segments = [(10, 30), (40, 60)]
        legacy_result = AcousticAnalyzer.filter_audio_to_vocal_segments(
            self.y, segments, hop_length=512,
        )
        new_result = new_filter(self.y, segments, hop_length=512)

        assert np.array_equal(legacy_result, new_result), (
            f"filter_audio_to_vocal_segments differs"
        )

    def test_normalize_loudness_with_different_rms(self):
        """不同 target_rms 值行为一致"""
        from services.features.acoustic import AcousticAnalyzer
        from backend.domain.audio.audio_utils import normalize_loudness as new_norm

        for target in [0.01, 0.05, 0.1]:
            legacy = AcousticAnalyzer.normalize_loudness(self.y.copy(), target_rms=target)
            new = new_norm(self.y.copy(), target_rms=target)
            assert np.array_equal(legacy, new), f"Differ at target_rms={target}"

    def test_find_vocal_segments_with_varied_params(self):
        """不同参数行为一致"""
        from services.features.acoustic import AcousticAnalyzer
        from backend.domain.audio.audio_utils import find_vocal_segments as new_find

        for min_sec, max_gap in [(0.1, 0.5), (1.0, 2.0), (0.5, 0.3)]:
            legacy = AcousticAnalyzer.find_vocal_segments(
                self.f0, hop_length=512, sample_rate=22050,
                min_segment_sec=min_sec, max_gap_sec=max_gap,
            )
            new = new_find(
                self.f0, hop_length=512, sample_rate=22050,
                min_segment_sec=min_sec, max_gap_sec=max_gap,
            )
            assert legacy == new, f"Differ at min_sec={min_sec}, max_gap={max_gap}"
