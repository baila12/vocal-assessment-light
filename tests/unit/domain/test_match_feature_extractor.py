"""
MatchFeatureExtractor 特征提取器测试 — TDD RED (v7.14 auto-match)

确定性合成音频 → 提取 MatchFeatures:
120BPM 节拍器 / A3 纯正弦 (220Hz) / 静音 / 短音频 / 白噪声。
"""
import numpy as np
import pytest

from backend.domain.song_match.feature_extractor import MatchFeatureExtractor

SR = 22050


def _metronome_120bpm(duration=6.0, bpm=120.0, sr=SR):
    """120 BPM 节拍器: 每 0.5s 一个 50ms 1kHz 衰减 burst"""
    n = int(sr * duration)
    y = np.zeros(n)
    hop = int(0.05 * sr)
    beat_interval = 60.0 / bpm
    for start in np.arange(0.0, duration, beat_interval):
        i0 = int(start * sr)
        i1 = min(i0 + hop, n)
        tt = np.arange(i1 - i0) / sr
        y[i0:i1] += np.sin(2 * np.pi * 1000 * tt) * np.exp(-tt * 40) * 0.8
    return y.astype(np.float32)


def _sine(freq=220.0, duration=2.0, sr=SR):
    """指定频率纯正弦"""
    t = np.linspace(0.0, duration, int(sr * duration), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * 0.8).astype(np.float32)


def _noise(seed=42, duration=2.0, sr=SR):
    rng = np.random.RandomState(seed)
    return (rng.randn(int(sr * duration)) * 0.3).astype(np.float32)


class TestMatchFeatureExtractor:
    """BPM / chroma / 调性 / 时长提取"""

    def test_extract_metronome_120bpm(self):
        features = MatchFeatureExtractor.extract(_metronome_120bpm())
        assert 100.0 <= features.bpm <= 140.0
        assert features.duration_seconds == pytest.approx(6.0, abs=0.01)

    def test_extract_a3_sine_chroma_peak_at_a(self):
        """220Hz = A3 → 平均 chroma 主峰位于 pitch class A (index 9)"""
        features = MatchFeatureExtractor.extract(_sine(220.0))
        peak_index = int(max(range(12), key=lambda i: features.chroma[i]))
        assert peak_index in (8, 9, 10)  # 容许 chroma_stft 边缘泄漏
        assert features.duration_seconds == pytest.approx(2.0, abs=0.01)

    def test_extract_silence(self):
        """静音 → bpm=0, chroma 全 0, 调性置信度 0"""
        features = MatchFeatureExtractor.extract(np.zeros(int(SR * 2), dtype=np.float32))
        assert features.bpm == 0.0
        assert all(c == 0.0 for c in features.chroma)
        assert features.key_confidence == 0.0

    def test_extract_short_audio_tolerant(self):
        """0.4s 短音频 → 不崩溃, 时长正确, bpm 非负"""
        features = MatchFeatureExtractor.extract(_sine(220.0, duration=0.4))
        assert features.duration_seconds == pytest.approx(0.4, abs=0.01)
        assert features.bpm >= 0.0

    def test_extract_noise_robust(self):
        """白噪声 → 不崩溃, 输出契约不变"""
        features = MatchFeatureExtractor.extract(_noise())
        assert features.bpm >= 0.0
        assert len(features.chroma) == 12
        assert 0.0 <= features.key_confidence <= 1.0

    def test_extract_detected_key_consistent_with_chroma(self):
        """A3 正弦 → 检测调性 pitch class 与 chroma 主峰一致 (A=9, 允许 ±1)"""
        from backend.domain.song_match.services import KeyDetector

        features = MatchFeatureExtractor.extract(_sine(220.0))
        peak_index = int(max(range(12), key=lambda i: features.chroma[i]))
        pc = KeyDetector.pitch_class(features.detected_key)
        assert pc is not None
        assert abs(pc - peak_index) <= 1
