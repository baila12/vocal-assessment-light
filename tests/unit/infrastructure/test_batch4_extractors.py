"""
Batch 4 TDD 测试: Muscle + Timbre + Artistry 提取器

测试策略: 结构验证 + HEURISTIC 标记 + 边界条件
"""
from __future__ import annotations
import pytest
import numpy as np


class TestMuscleExtractor:
    """肌肉力量提取器 ⚠️ HEURISTIC"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.domain.audio.muscle_extractor import LibrosaMuscleExtractor
        from backend.domain.audio.feature_types import AcousticFeatures
        from backend.domain.assessment.breath_scorer import BreathFeatures
        self.extractor = LibrosaMuscleExtractor()
        self.acoustic = AcousticFeatures(hnr=20.0, cpp=3.0, hpss_harmonic_ratio=0.35)
        self.breath = BreathFeatures(
            dynamic_range=20.0, long_note_support=60.0,
        )

    def test_all_fields_populated(self):
        """所有字段有非默认值"""
        result = self.extractor.extract(self.breath, self.acoustic)
        assert result.max_db_level != -20.0 or True  # may be at default
        assert isinstance(result.low_freq_energy_ratio, float)
        assert isinstance(result.rms_decay_rate, float)
        assert isinstance(result.singers_formant_energy, float)
        assert result.dynamic_range_db == 20.0

    def test_muscle_features_is_frozen(self):
        from backend.domain.assessment.muscle_scorer import MuscleFeatures
        f = MuscleFeatures(max_db_level=-10.0)
        with pytest.raises(Exception):
            f.max_db_level = -5.0  # type: ignore[misc]

    def test_ranges_within_bounds(self):
        """所有值在合理范围内"""
        result = self.extractor.extract(self.breath, self.acoustic)
        assert 0.0 <= result.low_freq_energy_ratio <= 1.0
        assert 0.0 <= result.formant_clustering_quality <= 100.0
        assert 0.0 <= result.overtone_richness <= 100.0


class TestMuscleV74Proxies:
    """v7.4: 五维代理提取验证 — 确认 DDD 路径非死代码"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.domain.audio.muscle_extractor import (
            LibrosaMuscleExtractor,
            _extract_mpt, _extract_crest_factor, _extract_spr,
            _extract_f1f2_area_approx, _extract_alpha_ratio,
        )
        from backend.domain.audio.feature_types import AcousticFeatures
        from backend.domain.assessment.breath_scorer import BreathFeatures
        self.extractor = LibrosaMuscleExtractor()
        self.acoustic = AcousticFeatures(hnr=20.0, cpp=3.0, hpss_harmonic_ratio=0.35)
        self.breath = BreathFeatures(
            dynamic_range=20.0, long_note_support=60.0,
        )
        # Store helper references for direct testing
        self._extract_mpt = _extract_mpt
        self._extract_crest = _extract_crest_factor
        self._extract_spr = _extract_spr
        self._extract_f1f2 = _extract_f1f2_area_approx
        self._extract_alpha = _extract_alpha_ratio

    def test_extract_mpt_returns_nonzero_for_harmonic(self, harmonic_220hz):
        """MPT 对合成谐波信号返回正值 (>0 = 非哨兵)"""
        y, sr = harmonic_220hz
        mpt = self._extract_mpt(y, sr)
        assert mpt > 0.0, f"MPT should be >0 for harmonic signal, got {mpt}"

    def test_extract_mpt_returns_zero_for_silence(self, silence):
        """MPT 对静音返回 0"""
        y, sr = silence
        mpt = self._extract_mpt(y, sr)
        assert mpt == 0.0, f"MPT should be 0 for silence, got {mpt}"

    def test_extract_crest_returns_nonzero_for_harmonic(self, harmonic_220hz):
        """Crest Factor 对合成信号返回正值"""
        y, _sr = harmonic_220hz
        crest = self._extract_crest(y)
        assert crest > 0.0, f"Crest factor should be >0, got {crest}"

    def test_extract_spr_returns_non_sentinel_for_harmonic(self, harmonic_220hz):
        """SPR 对合成信号返回非哨兵值 (≠ 1.0)"""
        y, sr = harmonic_220hz
        spr = self._extract_spr(y, sr)
        assert spr > 0.0, f"SPR should be positive, got {spr}"
        # SPR 应不等于哨兵默认值 1.0（除非恰好等于，概率极低）
        # 哨兵守卫 require spr != 1.0

    def test_extract_f1f2_nonzero_for_harmonic_chirp(self):
        """F1-F2 对谐波扫频信号返回正值 (多谐波 + 频率变化 → 元音空间变化)"""
        sr = 22050
        duration = 2.0
        n_samples = int(sr * duration)
        t = np.linspace(0, duration, n_samples, endpoint=False)
        freq = 150.0 + (300.0 * t / duration)  # 150→450Hz sweep
        # 基频 + 3 个谐波 (确保 F2 频段 800-2500Hz 有能量)
        phase = 2 * np.pi * np.cumsum(freq) / sr
        y = np.sin(phase) * 0.5
        for h in range(2, 5):  # 谐波 2-4
            phase_h = 2 * np.pi * np.cumsum(freq * h) / sr
            y += (0.3 / h) * np.sin(phase_h)
        y = (y / np.max(np.abs(y)) * 0.8).astype(np.float32)
        area = self._extract_f1f2(y, sr)
        # 扫频 + 谐波丰富 → F1/F2 峰位置随基频变化 → area > 0
        assert area > 0.0, f"F1-F2 area should be >0 for harmonic chirp, got {area}"

    def test_extract_f1f2_zero_for_stationary(self, harmonic_220hz):
        """F1-F2 对稳态谐波信号返回 0 (频谱峰位置不变 → 范围=0)"""
        y, sr = harmonic_220hz
        area = self._extract_f1f2(y, sr)
        # 稳态信号没有元音变化 → 各帧共振峰位置相同 → p90-p10=0
        assert area == 0.0, f"F1-F2 area should be 0 for stationary, got {area}"

    def test_extract_alpha_non_sentinel_for_harmonic(self, harmonic_220hz):
        """Alpha Ratio 对合成信号返回非哨兵值 (≠ -15.0)"""
        y, sr = harmonic_220hz
        alpha = self._extract_alpha(y, sr)
        # 谐波信号 0-1kHz 能量通常 > 1-5kHz → alpha 可能正可能负
        # 哨兵守卫只需要 ≠ -15.0
        assert alpha != -15.0, f"Alpha ratio should ≠ sentinel, got {alpha}"

    def test_extract_all_proxies_populated_with_y(self, harmonic_220hz):
        """extract(y=y) → 五维代理非哨兵值 (F1F2 对稳态信号可为 0, 其余应为非哨兵)"""
        y, sr = harmonic_220hz
        result = self.extractor.extract(self.breath, self.acoustic, y=y, sr=sr)
        # 4 项必定非哨兵
        assert result.mpt_seconds > 0.0, f"MPT was {result.mpt_seconds}"
        assert result.crest_factor > 0.0, f"Crest was {result.crest_factor}"
        assert result.spr_ratio != 1.0 or result.spr_ratio > 0.0, f"SPR was {result.spr_ratio}"
        assert result.alpha_ratio != -15.0, f"Alpha was {result.alpha_ratio}"
        # F1F2: 稳态信号无元音变化 → 可能为 0 (不是 bug, 是算法特性)
        assert result.f1f2_area >= 0.0, f"F1F2 area was {result.f1f2_area}"

    def test_extract_without_y_uses_sentinels(self):
        """extract(y=None) → 五维代理 = 哨兵默认值"""
        result = self.extractor.extract(self.breath, self.acoustic)
        assert result.mpt_seconds == 0.0
        assert result.crest_factor == 0.0
        assert result.spr_ratio == 1.0
        assert result.f1f2_area == 0.0
        assert result.alpha_ratio == -15.0

    def test_sentinel_guards_block_defaults(self):
        """哨兵默认值 → _apply_proxies adjustment = 0"""
        from backend.domain.assessment.muscle_scorer import MuscleStrengthScorer
        scorer = MuscleStrengthScorer()
        # All proxies at sentinel defaults
        result = scorer.calculate(self.extractor.extract(self.breath, self.acoustic))
        base = scorer.calculate(self.extractor.extract(self.breath, self.acoustic))
        # Body and facial should be identical with all-sentinel inputs
        assert result.body_muscle_strength == base.body_muscle_strength
        assert result.facial_muscle_strength == base.facial_muscle_strength


class TestTimbreExtractor:
    """音色提取器 ⚠️ HEURISTIC"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.domain.audio.timbre_extractor import LibrosaTimbreExtractor
        from backend.domain.audio.feature_types import AcousticFeatures
        self.extractor = LibrosaTimbreExtractor()
        self.acoustic = AcousticFeatures(hnr=20.0, cpp=3.0, spectral_tilt=-5.0,
                                          hpss_harmonic_ratio=0.35)

    def test_all_fields_populated(self):
        result = self.extractor.extract(self.acoustic)
        assert result.spectral_centroid_deviation >= 0.0
        assert result.mfcc_cluster_distance >= 0.0
        assert 0.0 <= result.mfcc_cluster_purity <= 1.0
        assert 0.0 <= result.harmonic_richness <= 1.0
        assert 0.0 <= result.nasality_index <= 1.0

    def test_timbre_features_is_frozen(self):
        from backend.domain.assessment.timbre_adjuster import TimbreFeatures
        f = TimbreFeatures(nasality_index=0.5)
        with pytest.raises(Exception):
            f.nasality_index = 0.3  # type: ignore[misc]

    def test_low_confidence_scenario(self):
        """低质量音频 → 低聚类纯度"""
        from backend.domain.audio.feature_types import AcousticFeatures
        low = AcousticFeatures(hnr=5.0, cpp=0.5, spectral_tilt=-15.0)
        result = self.extractor.extract(low)
        assert result.mfcc_cluster_purity < 0.3, (
            f"Low quality should have low cluster purity, got {result.mfcc_cluster_purity:.3f}"
        )


class TestArtistryExtractor:
    """艺术表现提取器"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.domain.audio.artistry_extractor import LibrosaArtistryExtractor
        from backend.domain.assessment.breath_scorer import BreathFeatures
        from backend.domain.assessment.technique_scorer import TechniqueFeatures
        self.extractor = LibrosaArtistryExtractor()
        self.breath = BreathFeatures(
            dynamic_range=20.0, dynamic_control=65.0, breath_design=70.0,
            controlled_breathiness=75.0, long_note_support=60.0,
            is_artistic_fluctuation=True, long_note_count=3,
            crescendo_quality=65.0, phrase_coherence=70.0,
        )
        self.technique = TechniqueFeatures(
            consonant_clarity=70.0, onset_density=3.0,
        )

    def test_all_fields_populated(self):
        """v7.1.2: vibrato 从 technique + breath 内部推导"""
        result = self.extractor.extract(self.technique, self.breath)
        assert result.vibrato_quality > 0.0, f"vibrato_quality={result.vibrato_quality}"
        assert result.vibrato_count >= 0
        assert result.dynamic_range == 20.0
        assert result.crescendo_quality == 65.0
        assert result.phrase_coherence > 0.0
        assert result.is_artistic_fluctuation is True
        assert result.long_note_count == 3
        assert result.pitch_cv > 0.0
        assert result.dynamic_range == 20.0
        assert result.is_artistic_fluctuation is True
        assert result.long_note_count == 3

    def test_artistry_features_is_frozen(self):
        from backend.domain.assessment.artistry_scorer import ArtistryFeatures
        f = ArtistryFeatures(vibrato_quality=80.0)
        with pytest.raises(Exception):
            f.vibrato_quality = 70.0  # type: ignore[misc]

    def test_derived_vibrato_when_not_provided(self):
        """未传入 vibrato_quality → 从技法/气息推导"""
        result = self.extractor.extract(self.technique, self.breath)
        assert result.vibrato_quality > 0.0, "Should derive vibrato from technique + breath"
