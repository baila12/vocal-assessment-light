"""
合成音频 fixtures — 用于 TDD 特征提取器测试

所有 fixtures 生成确定性合成信号, 无需真实音频文件。
"""
import numpy as np
import pytest

DEFAULT_SR = 22050
DEFAULT_DURATION = 2.0


def _make_audio(signal_fn, duration=DEFAULT_DURATION, sr=DEFAULT_SR):
    """通用音频生成器"""
    n_samples = int(sr * duration)
    y = signal_fn(n_samples, sr)
    return y.astype(np.float32), sr


@pytest.fixture(scope="module")
def sine_220hz():
    """纯 220Hz 正弦波, 2秒, 采样率 22050"""
    def _signal(n_samples, sr):
        t = np.linspace(0, n_samples / sr, n_samples, endpoint=False)
        return np.sin(2 * np.pi * 220 * t) * 0.8
    return _make_audio(_signal)


@pytest.fixture(scope="module")
def harmonic_220hz():
    """220Hz 基频 + 8 次谐波复合信号, 2秒"""
    def _signal(n_samples, sr):
        t = np.linspace(0, n_samples / sr, n_samples, endpoint=False)
        sig = np.zeros(n_samples)
        for h in range(1, 9):
            sig += (0.5 / h) * np.sin(2 * np.pi * 220 * h * t)
        sig /= np.max(np.abs(sig))
        return sig * 0.8
    return _make_audio(_signal)


@pytest.fixture(scope="module")
def white_noise():
    """白噪声, 2秒, 固定种子"""
    def _signal(n_samples, sr):
        rng = np.random.RandomState(42)
        return rng.randn(n_samples) * 0.3
    return _make_audio(_signal)


@pytest.fixture(scope="module")
def silence():
    """静音 (全零), 2秒"""
    def _signal(n_samples, sr):
        return np.zeros(n_samples)
    return _make_audio(_signal)


@pytest.fixture(scope="module")
def bright_signal():
    """高频丰富信号: 2kHz 正弦 + 白噪声(低振幅), 2秒"""
    def _signal(n_samples, sr):
        t = np.linspace(0, n_samples / sr, n_samples, endpoint=False)
        tone = np.sin(2 * np.pi * 2000 * t) * 0.7
        rng = np.random.RandomState(42)
        noise = rng.randn(n_samples) * 0.05
        return tone + noise
    return _make_audio(_signal)


@pytest.fixture(scope="module")
def dark_signal():
    """低频丰富信号: 100Hz 正弦 + 谐波衰减, 2秒"""
    def _signal(n_samples, sr):
        t = np.linspace(0, n_samples / sr, n_samples, endpoint=False)
        sig = np.zeros(n_samples)
        for h in range(1, 5):
            sig += (0.6 / h) * np.sin(2 * np.pi * 100 * h * t)
        sig /= np.max(np.abs(sig))
        return sig * 0.8
    return _make_audio(_signal)


@pytest.fixture(scope="module")
def sine_sweep():
    """220Hz 正弦 + 小幅频率抖动, 2秒"""
    def _signal(n_samples, sr):
        t = np.linspace(0, n_samples / sr, n_samples, endpoint=False)
        freq = 220 + 10 * np.sin(2 * np.pi * 0.5 * t)  # ±10Hz wobble
        phase = 2 * np.pi * np.cumsum(freq) / sr
        return np.sin(phase) * 0.8
    return _make_audio(_signal)
