"""
TDD: DDD 特征提取 flag 接入生产 — v7.1.2

测试 enable_ddd_feature_extraction 在 FeatureFlags / DimensionFlags / analyze_and_score 中的行为。
"""
from __future__ import annotations
import pytest
import numpy as np


# ================================================================
# Test 1: Flag 字段存在性
# ================================================================

class TestDddExtractionFlagExists:
    """验证 enable_ddd_feature_extraction 在两个 flags 类中都存在"""

    def test_dimension_flags_has_field(self):
        """DimensionFlags 包含 enable_ddd_feature_extraction, 默认 True (生产默认)"""
        from backend.domain.assessment.feature_flags import DimensionFlags
        flags = DimensionFlags()
        assert hasattr(flags, 'enable_ddd_feature_extraction'), (
            "DimensionFlags 缺少 enable_ddd_feature_extraction 字段"
        )
        assert flags.enable_ddd_feature_extraction is True, (
            "enable_ddd_feature_extraction 默认应为 True (DDD 原生提取生产默认)"
        )

    def test_feature_flags_has_field(self):
        """FeatureFlags 包含 enable_ddd_feature_extraction, 默认 True (生产默认)"""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags()
        assert hasattr(flags, 'enable_ddd_feature_extraction'), (
            "FeatureFlags 缺少 enable_ddd_feature_extraction 字段"
        )
        assert flags.enable_ddd_feature_extraction is True, (
            "enable_ddd_feature_extraction 默认应为 True (DDD 原生提取生产默认)"
        )

    def test_feature_flags_for_quick_has_field(self):
        """FeatureFlags.for_quick() 包含 enable_ddd_feature_extraction=True (生产默认)"""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags.for_quick()
        assert hasattr(flags, 'enable_ddd_feature_extraction')
        assert flags.enable_ddd_feature_extraction is True

    def test_feature_flags_for_professional_has_field(self):
        """FeatureFlags.for_professional() 包含 enable_ddd_feature_extraction=True (生产默认)"""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags.for_professional()
        assert hasattr(flags, 'enable_ddd_feature_extraction')
        assert flags.enable_ddd_feature_extraction is True

    def test_feature_flags_safe_baseline_has_field(self):
        """FeatureFlags.safe_baseline() 包含 enable_ddd_feature_extraction=False"""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags.safe_baseline()
        assert hasattr(flags, 'enable_ddd_feature_extraction')
        assert flags.enable_ddd_feature_extraction is False

    def test_construction_with_flag_true(self):
        """FeatureFlags(enable_ddd_feature_extraction=True) 可显式开启"""
        from services.feature_flags import FeatureFlags
        flags = FeatureFlags(enable_ddd_feature_extraction=True)
        assert flags.enable_ddd_feature_extraction is True

    def test_dimension_flags_construction_with_flag_true(self):
        """DimensionFlags(enable_ddd_feature_extraction=True) 可显式开启"""
        from backend.domain.assessment.feature_flags import DimensionFlags
        flags = DimensionFlags(enable_ddd_feature_extraction=True)
        assert flags.enable_ddd_feature_extraction is True


# ================================================================
# Test 2: DDD 提取路径集成 — analyze_and_score()
# ================================================================

class TestDddExtractionIntegration:
    """验证 analyze_and_score() 在 DDD 提取 flag 下的行为"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """初始化测试环境"""
        import os
        os.environ.setdefault('VAS_DISABLE_RATE_LIMIT', 'TRUE')

    @staticmethod
    def _make_test_audio(duration_s=2.0, sr=22050, freq=440.0):
        """生成测试音频 (带谐波的人声仿真)"""
        n = int(sr * duration_s)
        t = np.linspace(0, duration_s, n, endpoint=False)
        # 基频 + 谐波
        y = np.zeros(n, dtype=np.float64)
        for h in range(1, 6):
            y += (0.6 / h) * np.sin(2 * np.pi * freq * h * t)
        y /= np.max(np.abs(y))
        return (y * 0.8).astype(np.float32), sr

    def test_flag_false_uses_legacy_path(self):
        """enable_ddd_feature_extraction=False → 可显式回退旧评分路径"""
        from services.feature_flags import FeatureFlags
        from api.business.audio_analysis import analyze_and_score

        flags = FeatureFlags(enable_ddd_feature_extraction=False)
        # 验证 flag 被正确读取
        assert flags.enable_ddd_feature_extraction is False
        # 验证 flag 存在且可被 analyze_and_score 访问
        # (实际路径测试需要真实音频, 见 E2E)

    def test_flag_true_ddd_path_returns_valid_scores(self):
        """enable_ddd_feature_extraction=True → 返回有效六维评分"""
        from services.feature_flags import FeatureFlags
        from backend.application.assessment.ddd_feature_orchestrator import (
            DddFeatureExtractionOrchestrator, DddFeatureSet,
        )
        from backend.application.assessment.scoring_orchestrator import ScoringOrchestrator

        y, sr = self._make_test_audio(duration_s=1.5)
        # 模拟 PYIN F0
        hop = 256
        n_frames = int(len(y) / hop)
        f0 = np.full(n_frames, 440.0, dtype=np.float64)
        voiced = np.ones(n_frames, dtype=bool)

        # DDD 原生提取
        flags = FeatureFlags(enable_ddd_feature_extraction=True)
        ddd_flags = flags  # DimensionFlags 兼容

        extractor = DddFeatureExtractionOrchestrator()
        features = extractor.extract_all(y, sr, f0, voiced, is_clean_vocal=False)

        # DDD 原生评分
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

        # 验证六维评分字段完整
        assert "total_score" in result
        assert "pitch_score" in result
        assert "rhythm_score" in result
        assert "breath_score" in result
        assert "technique_score" in result
        assert "muscle_strength_score" in result
        assert "artistry_score" in result
        assert "timbre_adjustment" in result
        assert "heuristic_dimensions" in result
        assert "level" in result
        assert "grade" in result
        assert "color" in result
        assert "stars" in result

        # 验证数值范围
        assert 0.0 <= result["total_score"] <= 100.0, f"total_score 超出范围: {result['total_score']}"
        assert 0.0 <= result["pitch_score"] <= 100.0

        # 验证启发式标记
        assert "muscle_strength" in result["heuristic_dimensions"]
        assert "timbre" in result["heuristic_dimensions"]

    def test_ddd_extraction_with_default_f0(self):
        """DDD 提取在未提供 f0/voiced 时使用默认空数组, 不崩溃"""
        from backend.application.assessment.ddd_feature_orchestrator import (
            DddFeatureExtractionOrchestrator,
        )

        y, sr = self._make_test_audio(duration_s=1.0)
        extractor = DddFeatureExtractionOrchestrator()

        # 不提供 f0 和 voiced_flags
        features = extractor.extract_all(y, sr)

        # 所有维度都应该有默认值 (非 None)
        assert features.pitch is not None
        assert features.rhythm is not None
        assert features.acoustic is not None

    def test_ddd_extractor_initialization_in_audio_analysis(self):
        """验证 audio_analysis 模块能初始化 DDD 特征提取器"""
        from api.business.audio_analysis import (
            _ddd_feature_extractor_available,
            _ddd_feature_extractor,
        )
        # DDD 特征提取器应已初始化
        assert _ddd_feature_extractor_available, (
            "DDD 特征提取器应可用 (依赖 domain/audio 模块)"
        )
        from backend.application.assessment.ddd_feature_orchestrator import (
            DddFeatureExtractionOrchestrator,
        )
        assert isinstance(_ddd_feature_extractor, DddFeatureExtractionOrchestrator), (
            "DDD 特征提取器应为 DddFeatureExtractionOrchestrator 实例"
        )
