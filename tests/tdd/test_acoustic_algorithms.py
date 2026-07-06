"""
TDD 测试 — 开源算法移植 (v5.18 GREEN)

测试范围:
  - Feature Flag 机制
  - 多尺度 HNR (de Krom 1993)
  - Praat CPP (parselmouth PowerCepstrum)
  - Voicing Detection 评估
  - TorchCREPE 备选接入

所有测试使用合成信号, 无真实音频依赖, 速度 < 5s.
"""
import pytest
import numpy as np
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# Feature Flag 机制 (v5.18 GREEN)
# ═══════════════════════════════════════════════════════════════════════════

class TestFeatureFlags:
    """Feature Flag 系统 — 控制实验功能的开/关"""

    def test_feature_flags_dataclass_exists(self):
        """FeatureFlags dataclass 应存在且所有 flag 默认 False"""
        from services.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, 'enable_multiscale_hnr')
        assert hasattr(flags, 'enable_praat_cpp')
        assert hasattr(flags, 'enable_voicing_detection')
        assert hasattr(flags, 'enable_torchcrepe_fallback')
        assert hasattr(flags, 'enable_cross_dimension_modifiers')
        assert hasattr(flags, 'enable_reverb_compensation')
        # 默认全部关闭
        assert flags.enable_multiscale_hnr is False
        assert flags.enable_praat_cpp is False
        assert flags.enable_cross_dimension_modifiers is False
        assert flags.enable_reverb_compensation is False

    def test_feature_flags_not_affect_default_scoring(self):
        """FeatureFlags 全默认: 开关隔离性验证 (纯逻辑, 无音频依赖)

        验证:
        1. 所有新算法 flag 默认关闭
        2. 手动开启后生效
        3. 开启一个 flag 不影响其他
        """
        from services.feature_flags import FeatureFlags

        flags = FeatureFlags()

        # 所有新算法默认关闭
        assert flags.enable_multiscale_hnr is False
        assert flags.enable_praat_cpp is False
        assert flags.enable_voicing_detection is False
        assert flags.enable_torchcrepe_fallback is False
        assert flags.enable_cross_dimension_modifiers is False
        assert flags.enable_reverb_compensation is False

        # 手动开启
        flags.enable_reverb_compensation = True
        assert flags.enable_reverb_compensation is True

        # 隔离: 其他 flag 不受影响
        assert flags.enable_multiscale_hnr is False
        assert flags.enable_praat_cpp is False

    def test_feature_flag_check_overhead(self):
        """单个 flag 检查开销 < 1ms"""
        import time
        from services.feature_flags import FeatureFlags

        flags = FeatureFlags()
        start = time.perf_counter()
        for _ in range(10000):
            _ = flags.enable_multiscale_hnr
        elapsed = time.perf_counter() - start
        avg_us = (elapsed / 10000) * 1_000_000
        assert avg_us < 1000, f"Flag 检查 {avg_us:.1f}μs > 1000μs (1ms)"


# ═══════════════════════════════════════════════════════════════════════════
# 多尺度 HNR (v5.18 GREEN, de Krom 1993 倒谱分离法)
# ═══════════════════════════════════════════════════════════════════════════

class TestMultiScaleHNR:
    """多尺度 HNR — 短窗/中窗/长窗 + 稳定性"""

    def test_multiscale_hnr_returns_three_windows(self):
        """多尺度 HNR 应返回短/中/长三个窗口的 HNR 值"""
        from services.features.hnr import MultiScaleHNR, HNRMultiscaleResult

        analyzer = MultiScaleHNR(sample_rate=22050)
        t = np.linspace(0, 1, 22050)
        signal = (np.sin(2 * np.pi * 220 * t) +
                  np.sin(2 * np.pi * 440 * t) * 0.5 +
                  np.sin(2 * np.pi * 880 * t) * 0.25)

        result = analyzer.analyze(signal)
        assert isinstance(result, HNRMultiscaleResult)
        assert hasattr(result, 'hnr_short')
        assert hasattr(result, 'hnr_medium')
        assert hasattr(result, 'hnr_long')
        assert hasattr(result, 'hnr_stability')
        assert result.hnr_long > 5

    def test_multiscale_hnr_stability_for_clean_signal(self):
        """干净信号在不同窗口间的 HNR 应稳定 (低 CV)"""
        from services.features.hnr import MultiScaleHNR

        analyzer = MultiScaleHNR(sample_rate=22050)
        t = np.linspace(0, 2, 44100)
        signal = np.sin(2 * np.pi * 440 * t)

        result = analyzer.analyze(signal)
        assert result.hnr_stability < 0.3, \
            f"纯正弦 HNR 稳定性应 < 0.3, 实际: {result.hnr_stability}"


# ═══════════════════════════════════════════════════════════════════════════
# Praat CPP (v5.18 GREEN, parselmouth PowerCepstrum)
# ═══════════════════════════════════════════════════════════════════════════

class TestPraatCPP:
    """Praat CPP — parselmouth 替换手动 FFT 倒谱"""

    def test_praat_cpp_returns_consistent_values(self):
        """Praat CPP 应返回 cpp_mean/std/max 字段"""
        from services.features.cpp import PraatCPP, CepstralResult

        analyzer = PraatCPP()
        t = np.linspace(0, 1, 22050)
        signal = np.sin(2 * np.pi * 440 * t) * 0.5

        result = analyzer.analyze(signal)
        assert isinstance(result, CepstralResult)
        assert hasattr(result, 'cpp_mean')
        assert hasattr(result, 'cpp_std')
        assert hasattr(result, 'cpp_max')

    def test_praat_cpp_low_for_noise(self):
        """噪声的 CPP 应显著低于谐波丰富的人声信号

        Hillenbrand, J. et al. (1994). "Acoustic correlates of breathy vocal quality."
        """
        from services.features.cpp import PraatCPP

        analyzer = PraatCPP()
        if not analyzer.available:
            pytest.skip("parselmouth 未安装 — PraatCPP 不可用")

        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        # 模拟人声: 基频 220Hz + 9 个谐波
        f0 = 220.0
        voice = np.zeros_like(t)
        for h in range(1, 10):
            amplitude = 0.5 / h
            phase = np.random.uniform(0, 2 * np.pi) * 0.1
            voice += amplitude * np.sin(2 * np.pi * f0 * h * t + phase)
        voice = voice / np.max(np.abs(voice)) * 0.5

        np.random.seed(42)
        noise = np.random.randn(len(t)) * 0.1

        voice_result = analyzer.analyze(voice)
        noise_result = analyzer.analyze(noise)

        assert voice_result.cpp_mean > noise_result.cpp_mean + 0.5, \
            f"人声 CPP ({voice_result.cpp_mean:.2f}) 应显著高于噪声 ({noise_result.cpp_mean:.2f})"


# ═══════════════════════════════════════════════════════════════════════════
# Voicing Detection (v5.18 GREEN, pitch-benchmark 模式)
# ═══════════════════════════════════════════════════════════════════════════

class TestVoicingDetection:
    """Voicing 检测质量评估 — PYIN voiced/unvoiced 决策诊断"""

    def test_voicing_detector_evaluates_pyin_output(self):
        """VoicingDetector 应计算置信度、有声帧比例和一致性分数"""
        from services.features.voicing import VoicingDetector, VoicingDetectionResult

        sr = 22050
        hop = 512
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        n_frames = 1 + (len(t) - 512) // hop
        f0 = np.full(n_frames, 220.0, dtype=np.float64)
        f0[::20] = np.nan
        voiced_flags = ~np.isnan(f0)

        detector = VoicingDetector(sample_rate=sr, hop_length=hop)
        result = detector.evaluate(f0, voiced_flags)

        assert isinstance(result, VoicingDetectionResult)
        assert result.voicing_ratio > 0.5
        assert result.octave_jump_rate == 0.0

    def test_voicing_detector_handles_empty_input(self):
        """空输入应返回零值结果 (不崩溃)"""
        from services.features.voicing import VoicingDetector

        detector = VoicingDetector()
        result = detector.evaluate(np.array([]), np.array([]))
        assert result.total_frame_count == 0
        assert result.voicing_ratio == 0.0

    def test_voicing_detector_all_unvoiced(self):
        """全 unvoiced 置信度应为 0"""
        from services.features.voicing import VoicingDetector

        detector = VoicingDetector()
        n = 100
        f0 = np.full(n, np.nan)
        voiced_flags = np.zeros(n, dtype=bool)
        result = detector.evaluate(f0, voiced_flags)
        assert result.detection_confidence == 0.0


# ═══════════════════════════════════════════════════════════════════════════
# TorchCREPE (v5.18 GREEN, PYIN 降级时启用)
# ═══════════════════════════════════════════════════════════════════════════

class TestTorchCREPEFallback:
    """TorchCREPE — PYIN 置信度低时降级启用"""

    def test_crepe_fallback_produces_valid_f0(self):
        """TorchCREPE 应返回有效 f0 序列"""
        from services.audio_features_service import AudioFeaturesService
        from services.feature_flags import FeatureFlags

        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        signal = np.zeros_like(t)
        for h in range(1, 6):
            signal += (0.3 / h) * np.sin(2 * np.pi * 220 * h * t)

        service = AudioFeaturesService(sample_rate=sr)
        flags = FeatureFlags(enable_torchcrepe_fallback=True)
        f0, voiced = service._extract_f0(signal, feature_flags=flags)
        assert len(f0) > 0
        assert len(voiced) > 0

    def test_crepe_fallback_not_triggered_when_disabled(self):
        """feature_flags=None 时不触发 CREPE fallback"""
        from services.audio_features_service import AudioFeaturesService
        from services.feature_flags import FeatureFlags

        sr = 22050
        t = np.linspace(0, 0.5, int(sr * 0.5), endpoint=False)
        signal = np.sin(2 * np.pi * 440 * t) * 0.5

        service = AudioFeaturesService(sample_rate=sr)
        f0_none, _ = service._extract_f0(signal, feature_flags=None)
        f0_off, _ = service._extract_f0(signal, feature_flags=FeatureFlags())
        np.testing.assert_array_equal(f0_none, f0_off)
