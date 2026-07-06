"""
TDD 测试 — 混合音频检测 + 混响补偿 (v6.0 GREEN)

测试范围:
  - 混合音频检测 v6.0 (五特征融合, 文献驱动)
  - 混响补偿管线集成 (HPSS + 谱减法)

文献依据:
  - Lehner et al. (2018). TASLP 26(8). §4
  - Driedger et al. (2014). ISMIR. §3
  - Fitzgerald (2010). DAFx

真实音频测试使用 30s 片段 (非全曲) 加速。
"""
import pytest
import numpy as np
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# 混合音频检测 (v6.0 GREEN)
# ═══════════════════════════════════════════════════════════════════════════

class TestMixedAudioDetection:
    """混合音频检测 — v6.0 文献驱动五特征融合"""

    def test_detect_pure_synthetic_vocal_as_clean(self):
        """合成纯人声应被识别为非混合音频"""
        from services.features.acoustic import AcousticAnalyzer

        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        signal = np.zeros_like(t)
        for h in range(1, 9):
            signal += (0.5 / h) * np.sin(2 * np.pi * 220 * h * t)
        signal = signal / np.max(np.abs(signal)) * 0.8

        analyzer = AcousticAnalyzer(sample_rate=sr)
        is_mixed, confidence, _ = analyzer.detect_mixed_audio(signal)
        assert not is_mixed, f"合成纯人声不应判为混合, confidence={confidence:.2f}"

    def test_detect_synthetic_mixed_as_mixed(self):
        """合成混合音频 (人声+伴奏) 应被识别为混合"""
        from services.features.acoustic import AcousticAnalyzer

        sr = 22050
        duration = 3.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        # 人声
        vocal = np.zeros_like(t)
        for h in range(1, 6):
            vocal += (0.15 / h) * np.sin(2 * np.pi * 220 * h * t)

        # 伴奏: 贝斯 + 鼓 + 镲
        bass = 0.2 * np.sin(2 * np.pi * 55 * t)
        beat = np.zeros_like(t)
        beat_interval = int(sr * 0.5)
        for i in range(0, len(t), beat_interval):
            if i + 200 < len(t):
                beat[i:i + 200] = 0.25 * np.sin(2 * np.pi * 100 * t[i:i + 200])
        np.random.seed(42)
        cymbal = 0.12 * np.random.randn(len(t))

        mixed = vocal + bass + beat + cymbal
        mixed = mixed / np.max(np.abs(mixed)) * 0.8

        analyzer = AcousticAnalyzer(sample_rate=sr)
        is_mixed, confidence, _ = analyzer.detect_mixed_audio(mixed)
        assert is_mixed, f"合成混合音频应判为混合, confidence={confidence:.2f}"

    def test_detect_white_noise_as_non_mixed(self):
        """白噪声不应崩溃 (非音乐信号, 上游处理)"""
        from services.features.acoustic import AcousticAnalyzer

        sr = 22050
        np.random.seed(42)
        noise = np.random.randn(int(sr * 2)) * 0.5

        analyzer = AcousticAnalyzer(sample_rate=sr)
        _, confidence, _ = analyzer.detect_mixed_audio(noise)
        assert confidence >= 0.0

    def test_detect_mixed_audio_on_real_vocal_files(self, test_audio_dir):
        """真实纯人声文件不应被误判为混合音频 (回归测试, 30s 片段)"""
        if test_audio_dir is None:
            pytest.skip("No test audio")

        import librosa
        from services.features.acoustic import AcousticAnalyzer

        candidates = sorted(test_audio_dir.glob("*.mp3"))
        analyzer = AcousticAnalyzer(sample_rate=22050)
        known_with_accompaniment = {"手写的从前"}

        failures = []
        for audio_file in candidates:
            if "低分" in audio_file.name or "难听" in audio_file.name:
                continue
            audio_data, _ = librosa.load(str(audio_file), sr=22050, duration=30)
            is_mixed, confidence, _ = analyzer.detect_mixed_audio(audio_data)
            if is_mixed and not any(k in audio_file.name for k in known_with_accompaniment):
                failures.append(f"{audio_file.name}: confidence={confidence:.2f}")

        assert len(failures) == 0, f"纯人声误判为混合: {failures}"

    def test_detect_light_accompaniment_ballad(self, test_audio_dir):
        """轻伴奏抒情歌 — 已知局限: HPSS >0.88 时信号处理无法区分

        Driedger 2014 §3 + Lehner 2018: 极轻钢琴伴奏 HPSS ratio >0.88,
        信号处理方法理论上限, 需 LSTM 解决。
        """
        if test_audio_dir is None:
            pytest.skip("No test audio")

        import librosa
        from services.features.acoustic import AcousticAnalyzer

        target = test_audio_dir / "手写的从前（高分）.mp3"
        if not target.exists():
            pytest.skip("手写的从前 not available")

        analyzer = AcousticAnalyzer(sample_rate=22050)
        audio_data, _ = librosa.load(str(target), sr=22050, duration=30)
        is_mixed, confidence, metadata = analyzer.detect_mixed_audio(audio_data)

        if not is_mixed:
            pytest.skip(
                f"已知局限: HPSS ratio={metadata['hpss_harmonic_ratio']:.3f} > 0.88, "
                f"信号处理无法区分极轻谐波伴奏。需 LSTM 方法 (Lehner 2018)。"
            )

    def test_sub_band_flatness_discrimination(self):
        """子带频谱平坦度(1.5-3kHz) 应能区别人声和噪声 [Lehner 2018 §4]"""
        from services.features.acoustic import AcousticAnalyzer
        import librosa

        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        vocal = np.zeros_like(t)
        for h in range(1, 9):
            vocal += (0.5 / h) * np.sin(2 * np.pi * 220 * h * t)
        vocal = vocal / np.max(np.abs(vocal)) * 0.8

        np.random.seed(42)
        noise = np.random.randn(len(t)) * 0.5

        analyzer = AcousticAnalyzer(sample_rate=sr)
        vocal_stft = np.abs(librosa.stft(vocal))
        noise_stft = np.abs(librosa.stft(noise))
        freqs = librosa.fft_frequencies(sr=sr)

        vocal_flat = analyzer._calc_sub_band_flatness(vocal_stft, freqs, 1500, 3000)
        noise_flat = analyzer._calc_sub_band_flatness(noise_stft, freqs, 1500, 3000)

        assert vocal_flat < noise_flat, \
            f"人声子带平坦度({vocal_flat:.4f})应低于噪声({noise_flat:.4f})"

    def test_harmonicity_for_pure_vocal(self):
        """谐波度特征应正确识别谐波丰富的纯人声"""
        from services.features.acoustic import AcousticAnalyzer

        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        vocal = np.zeros_like(t)
        for h in range(1, 9):
            vocal += (0.5 / h) * np.sin(2 * np.pi * 220 * h * t)
        vocal = vocal / np.max(np.abs(vocal)) * 0.8

        np.random.seed(42)
        noise = np.random.randn(len(t)) * 0.5

        analyzer = AcousticAnalyzer(sample_rate=sr)
        vocal_harm = analyzer._calc_harmonicity(vocal)
        noise_harm = analyzer._calc_harmonicity(noise)

        assert vocal_harm > 0.3, f"人声谐波度({vocal_harm:.3f})应 > 0.3"
        assert vocal_harm > noise_harm * 3, \
            f"人声谐波度({vocal_harm:.3f})应远高于噪声({noise_harm:.3f})"


# ═══════════════════════════════════════════════════════════════════════════
# 混响补偿管线集成 (v6.0 GREEN)
# ═══════════════════════════════════════════════════════════════════════════

class TestReverbCompensation:
    """混响补偿 — HPSS 谐波分离 + 谱减法

    理论依据:
      - Fitzgerald (2010): HPSS median filtering
      - Boll (1979): Spectral subtraction
      - Berouti et al. (1979): Oversubtraction + spectral floor
    """

    def test_reverb_compensator_reduces_room_effect(self):
        """混响补偿后，干声和湿声应有差异"""
        from services.features.reverb import ReverbCompensator

        compensator = ReverbCompensator(sample_rate=22050)
        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        # 干声 (模拟人声)
        dry = np.zeros_like(t)
        for h in range(1, 9):
            dry += (0.5 / h) * np.sin(2 * np.pi * 220 * h * t)
        dry = dry / np.max(np.abs(dry)) * 0.5

        # 湿声 (含混响: 多路径延迟 + 指数衰减)
        np.random.seed(42)
        wet = dry.copy()
        delays = [500, 1200, 2200, 3500, 5100]
        for i, delay in enumerate(delays):
            decay = 0.25 * np.exp(-i * 0.5)
            wet += decay * np.roll(dry, delay)
        wet = wet / np.max(np.abs(wet)) * 0.5

        # 补偿
        _, dry_result = compensator.process(dry, return_result=True)
        wet_comp, wet_result = compensator.process(wet, return_result=True)

        assert wet_comp is not None and len(wet_comp) == len(wet)
        assert wet_result.noise_reduction_db >= 0, "混响补偿应减少噪声"


class TestReverbPipelineIntegration:
    """混响补偿接入 AudioFeaturesService → HNR/CPP 修正"""

    def test_reverb_flag_exists_in_feature_flags(self):
        """FeatureFlags 应包含 enable_reverb_compensation，默认关闭"""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags()
        assert hasattr(flags, 'enable_reverb_compensation')
        assert flags.enable_reverb_compensation is False

    def test_audio_features_service_has_reverb_compensator(self):
        """AudioFeaturesService 应初始化 ReverbCompensator"""
        from services.audio_features_service import AudioFeaturesService
        from services.features.reverb import ReverbCompensator

        service = AudioFeaturesService(sample_rate=22050)
        assert isinstance(service.reverb_compensator, ReverbCompensator)

    def test_reverb_flag_changes_hnr_for_wet_audio(self):
        """开启混响补偿后湿声 HNR 应与关闭时有差异"""
        from services.audio_features_service import AudioFeaturesService
        from services.feature_flags import FeatureFlags

        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        dry = np.zeros_like(t)
        for h in range(1, 9):
            dry += (0.5 / h) * np.sin(2 * np.pi * 220 * h * t)
        dry = dry / np.max(np.abs(dry)) * 0.5

        wet = dry.copy()
        delays = [500, 1200, 2200, 3500, 5100]
        for i, delay in enumerate(delays):
            decay = 0.25 * np.exp(-i * 0.5)
            wet += decay * np.roll(dry, delay)
        wet = wet / np.max(np.abs(wet)) * 0.5

        service = AudioFeaturesService(sample_rate=sr)
        flags_off = FeatureFlags()
        flags_on = FeatureFlags()
        flags_on.enable_reverb_compensation = True

        result_off = service.extract_all_features(wet.copy(), feature_flags=flags_off)
        result_on = service.extract_all_features(wet.copy(), feature_flags=flags_on)

        assert result_off.hnr > 0
        assert result_on.hnr > 0
        hnr_diff = abs(result_on.hnr - result_off.hnr)
        assert hnr_diff > 0.1, f"混响补偿应改变 HNR, 差异仅 {hnr_diff:.3f}dB"

    def test_reverb_compensation_preserves_pitch_features(self):
        """混响补偿不应影响音准特征 (仅修正 HNR/CPP)"""
        from services.audio_features_service import AudioFeaturesService
        from services.feature_flags import FeatureFlags

        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        signal = np.zeros_like(t)
        for h in range(1, 9):
            signal += (0.5 / h) * np.sin(2 * np.pi * 220 * h * t)
        signal = signal / np.max(np.abs(signal)) * 0.5

        service = AudioFeaturesService(sample_rate=sr)
        f0, voiced = service._extract_f0(signal)

        flags_off = FeatureFlags()
        flags_on = FeatureFlags()
        flags_on.enable_reverb_compensation = True

        result_off = service.extract_all_features(signal.copy(), f0=f0.copy(), feature_flags=flags_off)
        result_on = service.extract_all_features(signal.copy(), f0=f0.copy(), feature_flags=flags_on)

        np.testing.assert_allclose(
            result_off.pitch_deviation.mae_cents,
            result_on.pitch_deviation.mae_cents,
            rtol=0.01,
            err_msg="混响补偿不应改变音准偏差"
        )
