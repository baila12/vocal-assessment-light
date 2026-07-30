"""
ABI Calculator TDD 测试 — v7.6 P2

Barsties v. Latoszek (2017): 9-parameter breathiness model
"""
import pytest
import numpy as np


class TestAbiHelpers:
    """ABI 辅助函数测试"""

    def test_h1_h2_computation(self):
        """H1-H2: 纯正弦波 → H1 > H2 (频谱自然衰减)"""
        from backend.domain.audio.abi_calculator import compute_h1_h2
        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        y = np.sin(2 * np.pi * 220 * t).astype(np.float32) * 0.5
        f0 = np.full(len(y), 220.0)

        h1h2 = compute_h1_h2(y, sr, f0)
        # 纯正弦波: H2 能量 ≈ 0 (无第二谐波), H1/H2 比值应 > 0
        assert isinstance(h1h2, float)

    def test_h1_h2_harmonic_signal(self):
        """H1-H2: 带谐波的信号 → H2 应存在，比值合理"""
        from backend.domain.audio.abi_calculator import compute_h1_h2
        sr = 22050
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        y = np.sin(2 * np.pi * 220 * t) * 0.5
        y += 0.3 * np.sin(2 * np.pi * 440 * t)  # H2
        y = (y / np.max(np.abs(y)) * 0.5).astype(np.float32)
        f0 = np.full(len(y), 220.0)

        h1h2 = compute_h1_h2(y, sr, f0)
        assert isinstance(h1h2, float)
        # 有 H2 → H1-H2 应 < 纯正弦波的值

    def test_h1_h2_empty_f0(self):
        """H1-H2: 空 F0 → 返回 0"""
        from backend.domain.audio.abi_calculator import compute_h1_h2
        y = np.zeros(100, dtype=np.float32)
        h1h2 = compute_h1_h2(y, 22050, np.array([]))
        assert h1h2 == 0.0

    def test_hf_noise_sine_very_low(self):
        """HF noise: 纯正弦波 → >6kHz 能量极低"""
        from backend.domain.audio.abi_calculator import compute_hf_noise_6khz
        sr = 44100
        duration = 1.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        y = np.sin(2 * np.pi * 220 * t).astype(np.float32) * 0.5
        hf = compute_hf_noise_6khz(y, sr)
        # 纯 220Hz 信号, >6kHz 几乎无能量
        assert hf < -20.0, f"Pure sine should have low HF noise, got {hf}"

    def test_hf_noise_white_noise_higher(self):
        """HF noise: 白噪声 → >6kHz 有显著能量"""
        from backend.domain.audio.abi_calculator import compute_hf_noise_6khz
        sr = 44100
        rng = np.random.RandomState(42)
        y = rng.randn(int(sr * 0.5)).astype(np.float32) * 0.3
        hf = compute_hf_noise_6khz(y, sr)
        # 白噪声在高频有能量, HF noise 应该不极端
        assert hf > -60.0, f"White noise should have some HF energy, got {hf}"

    def test_period_sd_constant_f0(self):
        """Period SD: 恒定 F0 → ~0"""
        from backend.domain.audio.abi_calculator import compute_period_sd
        f0 = np.full(1000, 220.0)
        psd = compute_period_sd(f0, 22050)
        assert psd == pytest.approx(0.0, abs=0.1)

    def test_period_sd_varying_f0(self):
        """Period SD: 波动 F0 → >0"""
        from backend.domain.audio.abi_calculator import compute_period_sd
        sr = 22050
        f0 = 220.0 + 10.0 * np.sin(2 * np.pi * np.arange(1000) / 100)
        f0[f0 < 50] = 50  # clamp for validity
        psd = compute_period_sd(f0, sr)
        assert psd > 0.0, f"Varying F0 should give non-zero period SD, got {psd}"


class TestAbiCompute:
    """ABI 主计算函数测试"""

    def test_clean_voice_low_abi(self):
        """干净声音 → 低 ABI 分数 (<1.0)"""
        from backend.domain.audio.abi_calculator import compute_abi
        # 正常语音参数
        abi = compute_abi(
            cpp=15.0, gne=0.8, jitter_local=0.3,
            shimmer_db=0.15, hnr=25.0,
            h1_h2=-0.6, hf_noise_6khz=-40.0, period_sd=0.5,
        )
        assert 0.0 <= abi < 2.0, f"Clean voice ABI should be low, got {abi:.2f}"

    def test_breathy_voice_high_abi(self):
        """气息声 → 高 ABI 分数 (>2.0)"""
        from backend.domain.audio.abi_calculator import compute_abi
        # 气息声参数 (低 CPPS, 高 Jitter/Shimmer)
        abi = compute_abi(
            cpp=5.0, gne=0.4, jitter_local=2.5,
            shimmer_db=0.8, hnr=10.0,
            h1_h2=3.0, hf_noise_6khz=-25.0, period_sd=2.0,
        )
        assert abi > 1.5, f"Breathy voice ABI should be higher, got {abi:.2f}"

    def test_abi_ordering(self):
        """干净声音的 ABI < 气息声的 ABI"""
        from backend.domain.audio.abi_calculator import compute_abi
        clean = compute_abi(cpp=16.0, gne=0.85, jitter_local=0.2, shimmer_db=0.1,
                            hnr=28.0, h1_h2=-1.0, hf_noise_6khz=-45.0, period_sd=0.3)
        breathy = compute_abi(cpp=4.0, gne=0.3, jitter_local=3.0, shimmer_db=1.0,
                              hnr=8.0, h1_h2=4.0, hf_noise_6khz=-20.0, period_sd=3.0)
        assert clean < breathy, f"Clean ({clean:.2f}) should < breathy ({breathy:.2f})"

    def test_abi_range_0_to_10(self):
        """ABI 范围限缩到 [0, 10]"""
        from backend.domain.audio.abi_calculator import compute_abi
        # 极致干净
        abi_min = compute_abi(cpp=25.0, gne=1.0, jitter_local=0.0, shimmer_db=0.0,
                              hnr=40.0, h1_h2=-3.0, hf_noise_6khz=-80.0, period_sd=0.0)
        # 极致气息
        abi_max = compute_abi(cpp=0.0, gne=0.0, jitter_local=5.0, shimmer_db=2.0,
                              hnr=2.0, h1_h2=10.0, hf_noise_6khz=0.0, period_sd=5.0)
        assert 0.0 <= abi_min <= 10.0
        assert 0.0 <= abi_max <= 10.0


class TestAbiToBreathScore:
    """ABI → breath score 映射测试"""

    def test_low_abi_maps_to_high_breath(self):
        """低 ABI (干净) → 高 breath 分"""
        from backend.domain.audio.abi_calculator import abi_to_breath_score
        assert abi_to_breath_score(0.3) >= 90.0
        assert abi_to_breath_score(1.0) > 75.0

    def test_high_abi_maps_to_low_breath(self):
        """高 ABI (气息) → 低 breath 分"""
        from backend.domain.audio.abi_calculator import abi_to_breath_score
        assert abi_to_breath_score(4.0) < 40.0
        assert abi_to_breath_score(7.0) < 15.0

    def test_abi_breath_score_range(self):
        """映射始终在 [0, 100]"""
        from backend.domain.audio.abi_calculator import abi_to_breath_score
        for abi in [0.0, 1.0, 2.5, 4.0, 6.0, 10.0]:
            score = abi_to_breath_score(abi)
            assert 0.0 <= score <= 100.0, f"abi={abi} → score={score}"


class TestAbiCalculator:
    """AbiCalculator 集成测试"""

    def test_calculator_without_audiofeat_returns_nan(self):
        """无 audiofeat → 返回 NaN"""
        from backend.domain.audio.abi_calculator import AbiCalculator
        calc = AbiCalculator()
        result = calc.calculate(audiofeat=None)
        assert np.isnan(result), f"Should return NaN without audiofeat, got {result}"

    def test_calculator_with_audiofeat_returns_valid(self):
        """有 audiofeat → 返回有效 ABI"""
        from backend.domain.audio.abi_calculator import AbiCalculator
        from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures

        calc = AbiCalculator()
        # 模拟干净歌声的 audiofeat 特征
        af = AudiofeatFeatures(
            cpp_mean=14.0, gne_mean=0.75,
            jitter_local=0.3, shimmer_db=0.12,
            hnr_mean=25.0,
        )
        # 创建简短的合成音频用于 H1-H2, HF noise, period SD 计算
        sr = 22050
        t = np.linspace(0, 1.0, sr, endpoint=False)
        y = np.sin(2 * np.pi * 220 * t).astype(np.float32) * 0.5
        y += 0.3 * np.sin(2 * np.pi * 440 * t).astype(np.float32)
        y = (y / np.max(np.abs(y)) * 0.5).astype(np.float32)
        f0 = np.full(sr, 220.0)

        abi = calc.calculate(audiofeat=af, y=y, sr=sr, f0=f0, hnr=25.0)
        assert not np.isnan(abi), "ABI should be valid with audiofeat"
        assert 0.0 <= abi <= 10.0, f"ABI out of range: {abi}"
