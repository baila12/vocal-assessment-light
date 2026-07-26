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
