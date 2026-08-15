"""ComparisonService 偏差契约测试 — v7.19 E1 消双轨

ComparisonService (services/comparison) 降级为纯偏差提供者:
  - 只产出 alignment + deviation 数据, 不再调用 legacy ComparisonScoringEngine
  - 评分统一由 DDD ComparisonScoringService 承担 (唯一评分入口)
对应 BDD dtw-demotion.feature "DTW 不再产出评分 — 只产出偏差数据"。
"""
import pytest
import numpy as np

from services.comparison.dtw_aligner import (
    DTWAligner,
    MultiFeatureSequence,
)
from services.comparison.deviation_calculator import (
    DeviationCalculator,
    DeviationResult,
)


def _features(n=120, freq=440.0, seed=0) -> MultiFeatureSequence:
    rng = np.random.RandomState(seed)
    return MultiFeatureSequence(
        pitch=np.ones(n) * freq,
        energy=rng.uniform(-25, -15, n),
        zcr=np.zeros(n),
        times=np.arange(n) * 512 / 22050,
        sample_rate=22050,
        hop_length=512,
    )


class TestComparisonServiceDeviationContract:
    """ComparisonService 只输出偏差数据, 不输出评分字段"""

    def setup_method(self):
        from services.comparison.comparison_service import ComparisonService
        self.service = ComparisonService(sample_rate=22050, hop_length=512)

    def _run_compare(self):
        std = _features()
        user = _features(seed=1)  # 略不同
        return self.service.compare_features(std, user, style='pop')

    def test_returns_deviation_data(self):
        """应返回偏差聚合数据 (avg_cents_error / 各维 avg_deviation / stability)"""
        result = self._run_compare()
        assert result.get('success') is True
        assert 'avg_cents_error' in result
        assert 'confidence' in result
        assert 'method' in result
        dims = result.get('dimensions', {})
        assert 'pitch' in dims and 'rhythm' in dims
        assert 'volume' in dims and 'breath' in dims
        assert 'avg_deviation' in dims['pitch']
        assert 'stability' in dims['breath']
        # v7.18 P1: 独立信号
        assert 'octave_error_rate' in result
        assert 'tempo_ratio' in result

    def test_no_scoring_fields(self):
        """E1: 不再输出评分字段 (score/level/dimensions 内 score/pitch_match_rate/...)

        BDD: scoring_engine.py 应输出偏差数据 (而非评分); 不应输出 dtw_score 等。
        """
        result = self._run_compare()
        # 顶层评分字段
        for banned in ('score', 'level', 'pitch_match_rate', 'rhythm_match_rate',
                       'suggestions', 'diagnosis', 'problem_summary'):
            assert banned not in result, f"不应输出评分字段 {banned}"
        # dimensions 内不应有 score
        dims = result.get('dimensions', {})
        for dim in dims.values():
            assert 'score' not in dim, f"维度不应包含 score 字段: {dim}"


class TestComparisonServiceScoringFree:
    """ComparisonService 不再持有 legacy 评分引擎 (消双轨架构不变量)"""

    def test_no_scoring_engine_attribute(self):
        """ComparisonService 不应再有 scoring_engine 属性"""
        from services.comparison.comparison_service import ComparisonService
        service = ComparisonService()
        assert not hasattr(service, 'scoring_engine'), \
            "E1: ComparisonService 不应再持有 legacy scoring_engine"

    def test_scoring_engine_module_deleted(self):
        """services/comparison/scoring_engine.py 应已删除 (BDD 架构不变量)"""
        import os
        path = os.path.join(os.path.dirname(__file__), '..', '..',
                            'services', 'comparison', 'scoring_engine.py')
        assert not os.path.exists(path), \
            "E1: services/comparison/scoring_engine.py 应已删除"


class TestComparisonWeightsSingleSource:
    """对比风格权重单一来源 (v7.19 E1)"""

    def test_service_weights_from_single_source(self):
        """ComparisonScoringService.STYLE_WEIGHTS 应引用 value_objects 单一来源"""
        from backend.domain.comparison import value_objects
        from backend.domain.comparison.services import ComparisonScoringService
        assert ComparisonScoringService.STYLE_WEIGHTS is value_objects.COMPARISON_STYLE_WEIGHTS, \
            "权重应单一来源 (value_objects), 不应另起一份"

    def test_default_weights_match_pop(self):
        """ComparisonScores 默认权重应等于 pop 风格权重"""
        from backend.domain.comparison import value_objects
        scores = value_objects.ComparisonScores()
        assert scores._weights == tuple(
            value_objects.COMPARISON_STYLE_WEIGHTS['pop'].values()
        ), "默认权重应与 pop 风格一致 (单一来源)"
