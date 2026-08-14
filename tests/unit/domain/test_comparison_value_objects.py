"""Comparison 值对象 TDD — v7.3 Phase 1"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest


def _make_dimension_score(score=80.0, avg_dev=10.0, max_dev=30.0, problems=0):
    """构造 DimensionComparisonScore 测试数据"""
    from backend.domain.comparison.value_objects import DimensionComparisonScore
    return DimensionComparisonScore(
        score=score, avg_deviation=avg_dev, max_deviation=max_dev,
        problem_count=problems, details=(),
    )


class TestDimensionComparisonScore:
    """DimensionComparisonScore 值对象测试"""

    def test_construction(self):
        """应能正常构造"""
        from backend.domain.comparison.value_objects import DimensionComparisonScore
        ds = DimensionComparisonScore(score=80.0, avg_deviation=10.0, max_deviation=30.0, problem_count=5, details=())
        assert ds.score == 80.0
        assert ds.avg_deviation == 10.0
        assert ds.max_deviation == 30.0
        assert ds.problem_count == 5

    def test_is_frozen(self):
        """应为不可变"""
        from backend.domain.comparison.value_objects import DimensionComparisonScore
        import dataclasses
        assert dataclasses.is_dataclass(DimensionComparisonScore)
        ds = DimensionComparisonScore(score=80.0, avg_deviation=10.0, max_deviation=30.0, problem_count=0, details=())
        with pytest.raises(dataclasses.FrozenInstanceError):
            ds.score = 90.0

    def test_score_clamped_to_range(self):
        """score 应在 [0, 100] 范围内"""
        from backend.domain.comparison.value_objects import DimensionComparisonScore
        # Valid: within range
        ds = DimensionComparisonScore(score=50.0, avg_deviation=0.0, max_deviation=0.0, problem_count=0, details=())
        assert 0.0 <= ds.score <= 100.0
        # Boundary values
        ds0 = DimensionComparisonScore(score=0.0, avg_deviation=0.0, max_deviation=0.0, problem_count=0, details=())
        assert ds0.score == 0.0
        ds100 = DimensionComparisonScore(score=100.0, avg_deviation=0.0, max_deviation=0.0, problem_count=0, details=())
        assert ds100.score == 100.0

    def test_defaults(self):
        """默认值应合理"""
        from backend.domain.comparison.value_objects import DimensionComparisonScore
        ds = DimensionComparisonScore()
        assert ds.score == 0.0
        assert ds.avg_deviation == 0.0
        assert ds.max_deviation == 0.0
        assert ds.problem_count == 0
        assert ds.details == ()


class TestComparisonScores:
    """ComparisonScores 聚合值对象测试"""

    def test_construction(self):
        """应能正常构造四维度评分"""
        from backend.domain.comparison.value_objects import ComparisonScores
        pitch = _make_dimension_score(score=85.0)
        rhythm = _make_dimension_score(score=75.0)
        volume = _make_dimension_score(score=65.0)
        breath = _make_dimension_score(score=70.0)
        scores = ComparisonScores(pitch=pitch, rhythm=rhythm, volume=volume, breath=breath)
        assert scores.pitch.score == 85.0
        assert scores.rhythm.score == 75.0
        assert scores.volume.score == 65.0
        assert scores.breath.score == 70.0

    def test_total_score_pop_weights(self):
        """流行风格权重: pitch=0.40, rhythm=0.30, volume=0.15, breath=0.15"""
        from backend.domain.comparison.value_objects import ComparisonScores
        scores = ComparisonScores(
            pitch=_make_dimension_score(score=80.0),
            rhythm=_make_dimension_score(score=80.0),
            volume=_make_dimension_score(score=80.0),
            breath=_make_dimension_score(score=80.0),
        )
        total = scores.weighted_total()
        # 80 * 0.40 + 80 * 0.30 + 80 * 0.15 + 80 * 0.15 = 80
        assert total == 80.0

    def test_total_score_varied(self):
        """不同分数应正确加权"""
        from backend.domain.comparison.value_objects import ComparisonScores
        scores = ComparisonScores(
            pitch=_make_dimension_score(score=100.0),
            rhythm=_make_dimension_score(score=50.0),
            volume=_make_dimension_score(score=0.0),
            breath=_make_dimension_score(score=75.0),
        )
        total = scores.weighted_total()
        expected = 100 * 0.40 + 50 * 0.30 + 0 * 0.15 + 75 * 0.15
        assert total == pytest.approx(expected, rel=0.01)

    def test_is_frozen(self):
        """应为不可变"""
        from backend.domain.comparison.value_objects import ComparisonScores
        import dataclasses
        scores = ComparisonScores(
            pitch=_make_dimension_score(), rhythm=_make_dimension_score(),
            volume=_make_dimension_score(), breath=_make_dimension_score(),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            scores.total_score = 90.0

    def test_level_from_total(self):
        """等级判定应与 ScoreLevel 一致"""
        from backend.domain.comparison.value_objects import ComparisonScores
        from backend.shared.domain_types import ScoreLevel

        cases = [(95.0, "专业级"), (85.0, "优秀"), (75.0, "良好"),
                 (55.0, "中等"), (35.0, "及格"), (15.0, "待改进")]
        for total, expected_label in cases:
            scores = ComparisonScores(
                pitch=_make_dimension_score(score=total),
                rhythm=_make_dimension_score(score=total),
                volume=_make_dimension_score(score=total),
                breath=_make_dimension_score(score=total),
            )
            level = ScoreLevel.from_score(scores.weighted_total())
            assert level.label == expected_label

    def test_with_confidence_adjustment(self):
        """v7.18 P2 (F4): 温和置信度调制 — conf 0.5 → ×0.75, 1.0 → 不变"""
        from backend.domain.comparison.value_objects import ComparisonScores
        scores = ComparisonScores(
            pitch=_make_dimension_score(score=80.0),
            rhythm=_make_dimension_score(score=80.0),
            volume=_make_dimension_score(score=80.0),
            breath=_make_dimension_score(score=80.0),
        )
        raw_total = scores.weighted_total()
        adjusted = scores.with_confidence(0.5)
        assert adjusted.weighted_total() == pytest.approx(raw_total * 0.75, rel=0.01)
        # confidence=1.0 → no change
        full = scores.with_confidence(1.0)
        assert full.weighted_total() == raw_total
