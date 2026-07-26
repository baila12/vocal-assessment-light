"""
TDD: DDD 路径 vs 适配器路径 评分对齐测试 — v7.1.3

验证两条评分路径对同一音频产生一致的结果。
测试 technique +3.4 和 muscle +4.1 对齐残差的修复。
"""
from __future__ import annotations
import pytest
import numpy as np


# ================================================================
# Test Fixtures
# ================================================================

def _make_test_audio(duration_s=2.0, sr=22050, freq=440.0):
    """生成测试音频 (带谐波的人声仿真, 带音量包络)"""
    n = int(sr * duration_s)
    t = np.linspace(0, duration_s, n, endpoint=False)
    # 基频 + 谐波
    y = np.zeros(n, dtype=np.float64)
    for h in range(1, 6):
        y += (0.6 / h) * np.sin(2 * np.pi * freq * h * t)
    # 音量包络 (渐入渐出)
    envelope = np.ones(n)
    attack = int(sr * 0.1)
    release = int(sr * 0.2)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    y *= envelope
    y /= np.max(np.abs(y))
    return (y * 0.8).astype(np.float32), sr


def _make_f0_from_audio(y, sr, hop_length=256):
    """从音频提取 F0, 模拟 PYIN 输出"""
    import librosa
    f0, voiced_flag, _ = librosa.pyin(
        y.astype(np.float64), fmin=65.0, fmax=1047.0, sr=sr,
        hop_length=hop_length, fill_na=0.0,
    )
    return f0, voiced_flag.astype(bool)


# ================================================================
# Test 1: TechniqueFeatures 对齐 — onset_density 来源一致性
# ================================================================

class TestTechniqueAlignment:
    """验证 DDD technique 提取器与适配器路径 onset_density 一致"""

    def test_onset_density_from_same_source(self):
        """DDD 和 adapter 的 onset_density 应来自同一 RhythmAlignmentResult"""
        y, sr = _make_test_audio(duration_s=2.0)
        f0, voiced = _make_f0_from_audio(y, sr)

        # Path A: DDD rhythm extractor
        from backend.domain.audio.rhythm_extractor import LibrosaRhythmExtractor
        ddd_rhythm = LibrosaRhythmExtractor(sample_rate=sr).extract(y, sr)

        # Both paths use RhythmAnalyzer internally → same beats_per_second
        # The key: technique.onset_density must match rhythm.onset_density
        from backend.domain.audio.technique_extractor import LibrosaTechniqueExtractor
        from backend.domain.audio.feature_types import AcousticFeatures

        ddd_acoustic = AcousticFeatures(hnr=15.0, cpp=1.0)
        ddd_technique = LibrosaTechniqueExtractor(sample_rate=sr).extract(
            y, sr, ddd_acoustic, f0=f0, onset_density=ddd_rhythm.onset_density,
        )

        # onset_density should be forwarded from rhythm → technique
        assert ddd_technique.onset_density == pytest.approx(ddd_rhythm.onset_density, rel=0.01), (
            f"DDD technique onset_density ({ddd_technique.onset_density}) "
            f"should match rhythm onset_density ({ddd_rhythm.onset_density})"
        )

    def test_technique_onset_density_fallback_to_independent(self):
        """未提供 onset_density 时，technique extractor 应自行计算（回退路径）"""
        y, sr = _make_test_audio(duration_s=1.5)
        from backend.domain.audio.technique_extractor import LibrosaTechniqueExtractor
        from backend.domain.audio.feature_types import AcousticFeatures

        ddd_acoustic = AcousticFeatures(hnr=15.0, cpp=1.0)
        # 不传入 onset_density
        ddd_technique = LibrosaTechniqueExtractor(sample_rate=sr).extract(
            y, sr, ddd_acoustic, f0=None, onset_density=None,
        )

        assert ddd_technique.onset_density > 0.0, (
            f"Fallback onset_density should be > 0, got {ddd_technique.onset_density}"
        )
        assert isinstance(ddd_technique.onset_density, float)


# ================================================================
# Test 2: MuscleFeatures 对齐 — formant_clustering_quality 来源
# ================================================================

class TestMuscleAlignment:
    """验证 DDD muscle 提取器与适配器路径 formant_clustering 一致"""

    def test_formant_cluster_uses_pitch_stability_long(self):
        """当 pitch_stability_long > 0 时，应用其作为 formant 聚类质量"""
        from backend.domain.audio.muscle_extractor import LibrosaMuscleExtractor
        from backend.domain.audio.feature_types import AcousticFeatures
        from backend.domain.assessment.breath_scorer import BreathFeatures

        breath = BreathFeatures(
            pitch_stability_long=75.0,
            long_note_support=50.0,
            dynamic_range=20.0,
            controlled_breathiness=60.0,
            long_note_decay=1.5,
        )
        acoustic = AcousticFeatures(hnr=18.0, hpss_harmonic_ratio=0.35)

        ddd_muscle = LibrosaMuscleExtractor().extract(breath, acoustic)

        # formant_clustering_quality 应反映 pitch_stability_long (75.0)
        assert ddd_muscle.formant_clustering_quality == pytest.approx(75.0, rel=0.05), (
            f"formant_clustering_quality ({ddd_muscle.formant_clustering_quality}) "
            f"should reflect pitch_stability_long (75.0)"
        )

    def test_formant_cluster_fallback_when_pitch_stability_zero(self):
        """当 pitch_stability_long = 0 时，应回退到 long_note_support"""
        from backend.domain.audio.muscle_extractor import LibrosaMuscleExtractor
        from backend.domain.audio.feature_types import AcousticFeatures
        from backend.domain.assessment.breath_scorer import BreathFeatures

        breath = BreathFeatures(
            pitch_stability_long=0.0,  # 未计算
            long_note_support=55.0,
            dynamic_range=20.0,
            controlled_breathiness=60.0,
            long_note_decay=1.5,
        )
        acoustic = AcousticFeatures(hnr=18.0, hpss_harmonic_ratio=0.35)

        ddd_muscle = LibrosaMuscleExtractor().extract(breath, acoustic)

        # 回退到 long_note_support (55.0)
        assert ddd_muscle.formant_clustering_quality == pytest.approx(55.0, rel=0.05), (
            f"formant_clustering_quality ({ddd_muscle.formant_clustering_quality}) "
            f"should fallback to long_note_support (55.0) when pitch_stability_long=0"
        )

    def test_muscle_alignment_ddd_vs_adapter(self):
        """DDD 和 adapter 对相同输入产生一致的 MuscleFeatures"""
        from backend.domain.audio.muscle_extractor import LibrosaMuscleExtractor
        from backend.domain.audio.feature_types import AcousticFeatures
        from backend.domain.assessment.breath_scorer import BreathFeatures
        from backend.application.assessment.feature_adapters import FeatureAdapterRegistry

        # 构造与 legacy BreathStabilityResult 一致的 BreathFeatures
        breath = BreathFeatures(
            pitch_stability_long=50.0,
            long_note_support=50.0,
            dynamic_range=15.0,
            controlled_breathiness=50.0,
            long_note_decay=1.0,
        )
        acoustic = AcousticFeatures(hnr=15.0, hpss_harmonic_ratio=0.30)

        # Path A: DDD muscle extractor
        ddd_muscle = LibrosaMuscleExtractor().extract(breath, acoustic)

        # Path B: adapter (simulated with same inputs)
        # Construct a mock features object that matches legacy AudioFeaturesResult
        from types import SimpleNamespace
        mock_features = SimpleNamespace(
            hnr=15.0,
            breath_stability=SimpleNamespace(
                pitch_stability_long=50.0,
                long_note_support_score=50.0,
                dynamic_range=15.0,
                controlled_breathiness=50.0,
                long_note_decay=1.0,
                _hpss_harmonic_ratio=0.30,
            ),
        )
        adapter_muscle = FeatureAdapterRegistry.to_muscle(mock_features)

        # 验证关键字段对齐
        assert ddd_muscle.max_db_level == pytest.approx(adapter_muscle.max_db_level, rel=0.01), (
            f"max_db_level: DDD={ddd_muscle.max_db_level} vs adapter={adapter_muscle.max_db_level}"
        )
        assert ddd_muscle.low_freq_energy_ratio == pytest.approx(
            adapter_muscle.low_freq_energy_ratio, rel=0.01
        ), f"low_freq_energy_ratio mismatch"
        assert ddd_muscle.rms_decay_rate == pytest.approx(adapter_muscle.rms_decay_rate, rel=0.01), (
            f"rms_decay_rate: DDD={ddd_muscle.rms_decay_rate} vs adapter={adapter_muscle.rms_decay_rate}"
        )
        assert ddd_muscle.singers_formant_energy == pytest.approx(
            adapter_muscle.singers_formant_energy, rel=0.01
        ), f"singers_formant_energy mismatch"
        assert ddd_muscle.formant_clustering_quality == pytest.approx(
            adapter_muscle.formant_clustering_quality, rel=0.01
        ), f"formant_clustering_quality: DDD={ddd_muscle.formant_clustering_quality} vs adapter={adapter_muscle.formant_clustering_quality}"
        assert ddd_muscle.overtone_richness == pytest.approx(
            adapter_muscle.overtone_richness, rel=0.01
        ), f"overtone_richness mismatch"
        assert ddd_muscle.dynamic_range_db == pytest.approx(
            adapter_muscle.dynamic_range_db, rel=0.01
        ), f"dynamic_range_db mismatch"


# ================================================================
# Test 3: DDD 端到端评分一致性 (v7.1.5 — 移除旧 adapter 对比)
# ================================================================

class TestE2EScoringConsistency:
    """验证 DDD 原生路径对合成音频产生一致的六维评分"""

    def test_ddd_scoring_on_synthetic_audio(self):
        """DDD 原生路径应对合成音频产生有效评分 (总分 0-100)"""
        y, sr = _make_test_audio(duration_s=2.0)
        f0, voiced = _make_f0_from_audio(y, sr)

        from backend.application.assessment.ddd_feature_orchestrator import (
            DddFeatureExtractionOrchestrator,
        )
        from backend.application.assessment.scoring_orchestrator import ScoringOrchestrator

        extractor = DddFeatureExtractionOrchestrator()
        features = extractor.extract_all(y, sr, f0, voiced, is_clean_vocal=True)

        scoring = ScoringOrchestrator()
        result = scoring.calculate_ddd(
            pitch=features.pitch, rhythm=features.rhythm,
            breath=features.breath, technique=features.technique,
            muscle=features.muscle, artistry=features.artistry,
            timbre=features.timbre,
        )

        # 验证六维评分完整性
        assert 'pitch_score' in result
        assert 'rhythm_score' in result
        assert 'breath_score' in result
        assert 'technique_score' in result
        assert 'muscle_strength_score' in result
        assert 'artistry_score' in result
        assert 0.0 <= result['total_score'] <= 100.0

        # 验证启发式标记
        assert 'muscle_strength' in result['heuristic_dimensions']
        assert 'timbre' in result['heuristic_dimensions']
