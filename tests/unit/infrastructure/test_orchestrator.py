"""
DDD Feature Orchestrator 集成测试 — v7.1 Batch 5

测试完整 DDD 链路: extract_all → calculate_ddd
"""
from __future__ import annotations
import pytest
import numpy as np


class TestDddFeatureOrchestrator:
    """DDD 特征编排器集成测试"""

    @pytest.fixture(autouse=True)
    def setup(self):
        from backend.application.assessment.ddd_feature_orchestrator import (
            DddFeatureExtractionOrchestrator,
        )
        self.orchestrator = DddFeatureExtractionOrchestrator()

    @staticmethod
    def _make_test_audio(duration_s=1.0, sr=22050, freq=440.0):
        n = int(sr * duration_s)
        t = np.linspace(0, duration_s, n, endpoint=False)
        y = (np.sin(2 * np.pi * freq * t) * 0.5).astype(np.float32)
        return y, sr

    @staticmethod
    def _make_f0(duration_s=1.0, sr=22050, freq=440.0, hop=256):
        n_frames = int(duration_s * sr / hop)
        f0 = np.full(n_frames, float(freq), dtype=np.float64)
        voiced = np.ones(n_frames, dtype=bool)
        return f0, voiced

    def test_extract_all_returns_all_dimensions(self):
        """extract_all 返回 7 个维度的特征"""
        y, sr = self._make_test_audio(duration_s=1.0)
        f0, voiced = self._make_f0(duration_s=1.0, sr=sr)
        features = self.orchestrator.extract_all(y, sr, f0, voiced)

        assert features.pitch is not None
        assert features.rhythm is not None
        assert features.breath is not None
        assert features.technique is not None
        assert features.muscle is not None
        assert features.artistry is not None
        assert features.timbre is not None
        assert features.acoustic is not None

    def test_extract_all_no_crash(self):
        """空输入不崩溃"""
        y = np.zeros(22050, dtype=np.float32)
        features = self.orchestrator.extract_all(y, 22050)
        assert features.pitch.mae_cents >= 0.0

    def test_calculate_ddd_full_integration(self):
        """完整 DDD 链路: extract_all → calculate_ddd → 全维度验证"""
        from backend.application.assessment.scoring_orchestrator import ScoringOrchestrator
        from backend.domain.assessment.pitch_scorer import PitchFeatures
        from backend.domain.assessment.rhythm_scorer import RhythmFeatures
        from backend.domain.assessment.breath_scorer import BreathFeatures
        from backend.domain.assessment.technique_scorer import TechniqueFeatures
        from backend.domain.assessment.muscle_scorer import MuscleFeatures
        from backend.domain.assessment.artistry_scorer import ArtistryFeatures
        from backend.domain.assessment.timbre_adjuster import TimbreFeatures

        y, sr = self._make_test_audio(duration_s=1.0)
        f0, voiced = self._make_f0(duration_s=1.0, sr=sr)
        features = self.orchestrator.extract_all(y, sr, f0, voiced)

        scoring = ScoringOrchestrator()
        result = scoring.calculate_ddd(
            pitch=features.pitch,
            rhythm=features.rhythm,
            breath=features.breath,
            technique=features.technique,
            muscle=features.muscle,
            artistry=features.artistry,
            timbre=features.timbre,
        )

        assert "total_score" in result
        assert 0.0 <= result["total_score"] <= 100.0
        assert "pitch_score" in result
        assert "muscle_strength_score" in result
        assert "timbre_adjustment" in result
        assert "heuristic_dimensions" in result
        assert "muscle_strength" in result["heuristic_dimensions"]
        assert "timbre" in result["heuristic_dimensions"]

        # DDD 路径使用真实特征数据验证 (非空默认值)
        empty_result = scoring.calculate_ddd(
            pitch=PitchFeatures(),
            rhythm=RhythmFeatures(),
            breath=BreathFeatures(),
            technique=TechniqueFeatures(),
            muscle=MuscleFeatures(),
            artistry=ArtistryFeatures(),
            timbre=TimbreFeatures(),
        )
        assert 0.0 <= empty_result["total_score"] <= 100.0
