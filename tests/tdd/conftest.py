"""
TDD 测试共享 Fixtures — v6.1 模块化

优化测试速度:
- 真实音频文件仅在会话级加载一次 (session scope)
- 合成信号测试不需要真实音频, 各自独立运行
- analyze_and_score 结果缓存: 同一文件不重复分析
"""
import pytest
import numpy as np
from pathlib import Path


# ── 测试数据路径 ──

@pytest.fixture(scope="session")
def test_audio_dir():
    """真实测试音频目录"""
    d = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
    if d.exists():
        return d
    return None


@pytest.fixture(scope="session")
def vocal_files(test_audio_dir):
    """所有真实人声测试文件列表 (按文件名排序)"""
    if test_audio_dir is None:
        return []
    return sorted(test_audio_dir.glob("*.mp3"))


@pytest.fixture(scope="session")
def good_vocal_file(vocal_files):
    """第一个高分音频文件"""
    for f in vocal_files:
        if "低分" not in f.name and "难听" not in f.name:
            return f
    return vocal_files[0] if vocal_files else None


@pytest.fixture(scope="session")
def bad_vocal_file(vocal_files):
    """第一个低分音频文件"""
    for f in vocal_files:
        if "低分" in f.name or "难听" in f.name:
            return f
    return None


# ── 合成信号 fixtures ──

@pytest.fixture(scope="session")
def harmonic_signal_220hz():
    """220Hz 基频 + 8 谐波 (模拟人声)"""
    sr = 22050
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = np.zeros_like(t)
    for h in range(1, 9):
        signal += (0.5 / h) * np.sin(2 * np.pi * 220 * h * t)
    return signal / np.max(np.abs(signal)) * 0.8


@pytest.fixture(scope="session")
def sine_440hz():
    """纯 440Hz 正弦波"""
    sr = 22050
    duration = 2.0
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return np.sin(2 * np.pi * 440 * t) * 0.5


@pytest.fixture(scope="session")
def white_noise():
    """白噪声"""
    sr = 22050
    duration = 2.0
    np.random.seed(42)
    return np.random.randn(int(sr * duration)) * 0.5


# ── 可选: 真音频分析结果缓存 (v6.1 预留, 测试间共享) ──

@pytest.fixture(scope="session")
def cached_quick_result(good_vocal_file):
    """
    对第一个高分音频的 Quick 模式分析结果 (会话级缓存).

    注意: 此 fixture 在首次使用时运行一次, 后续测试复用。
    适用于验证类测试 (分数范围/字段存在性), 不适用于
    需要独立分析结果的测试。
    """
    if good_vocal_file is None:
        return None

    from api.business.audio_analysis import analyze_and_score
    return analyze_and_score(str(good_vocal_file), mode='quick')


@pytest.fixture(scope="session")
def cached_bad_result(bad_vocal_file):
    """对低分音频的 Quick 模式结果 (会话级缓存)"""
    if bad_vocal_file is None:
        return None

    from api.business.audio_analysis import analyze_and_score
    return analyze_and_score(str(bad_vocal_file), mode='quick')
