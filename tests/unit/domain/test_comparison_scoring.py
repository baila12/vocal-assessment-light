"""Comparison 领域服务 TDD — v7.3 Phase 2"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest
from backend.domain.comparison.entities import DeviationData, AlignmentData
from backend.domain.comparison.value_objects import ComparisonScores, DimensionComparisonScore


class TestComparisonScoringService:
    """ComparisonScoringService 评分算法测试"""

    def setup_method(self):
        from backend.domain.comparison.services import ComparisonScoringService
        self.service = ComparisonScoringService()

    # ---- Pitch scoring ----

    def test_pitch_perfect(self):
        """0 音分偏差 → 100 分"""
        dev = DeviationData(avg_pitch_cents=0.0)
        result = self.service.score(dev, confidence=1.0)
        assert result.pitch.score == 100.0

    def test_pitch_minor_deviation(self):
        """25 音分 → ~87.5 分"""
        dev = DeviationData(avg_pitch_cents=25.0)
        result = self.service.score(dev, confidence=1.0)
        assert result.pitch.score == pytest.approx(87.5, rel=0.05)

    def test_pitch_major_deviation(self):
        """75 音分 → ~50 分"""
        dev = DeviationData(avg_pitch_cents=75.0)
        result = self.service.score(dev, confidence=1.0)
        assert result.pitch.score == pytest.approx(50.0, rel=0.1)

    def test_pitch_severe(self):
        """150 音分 → ~10 分 (保底)"""
        dev = DeviationData(avg_pitch_cents=150.0)
        result = self.service.score(dev, confidence=1.0)
        assert result.pitch.score >= 10.0
        assert result.pitch.score <= 25.0

    # ---- Rhythm scoring ----

    def test_rhythm_perfect(self):
        """<= 50ms → 100 分"""
        dev = DeviationData(avg_rhythm_ms=30.0)
        result = self.service.score(dev, confidence=1.0)
        assert result.rhythm.score == 100.0

    def test_rhythm_deviation(self):
        """100ms → ~90 分"""
        dev = DeviationData(avg_rhythm_ms=100.0)
        result = self.service.score(dev, confidence=1.0)
        assert result.rhythm.score == pytest.approx(90.0, rel=0.1)

    # ---- Volume scoring ----

    def test_volume_perfect(self):
        """v7.18 P1 (F3): 动态偏差 0 → 100 分 (z-score 语义, 录音增益已归一)"""
        dev = DeviationData(avg_volume_percent=0.0)
        result = self.service.score(dev, confidence=1.0)
        assert result.volume.score == 100.0

    def test_volume_dynamic_deviation(self):
        """v7.18 P1 (F3): 动态偏差 0.3 → 70 分 (测动态形状, 非绝对 dB)"""
        dev = DeviationData(avg_volume_percent=0.3)
        result = self.service.score(dev, confidence=1.0)
        assert result.volume.score == pytest.approx(70.0, rel=0.05)

    # ---- Breath scoring ----

    def test_breath_stable(self):
        """稳定性 0.9 → 90 分"""
        dev = DeviationData(avg_breath_stability=0.9)
        result = self.service.score(dev, confidence=1.0)
        assert result.breath.score == 90.0

    # ---- Total score ----

    def test_all_perfect_total_100(self):
        """所有维度完美 → 总分 100"""
        dev = DeviationData()
        result = self.service.score(dev, confidence=1.0)
        assert result.weighted_total() == 100.0

    def test_confidence_scales_total(self):
        """v7.18 P2 (F4): 温和置信度调制 — conf 0.5 → ×0.75 (非归零)"""
        dev = DeviationData(avg_pitch_cents=0.0)  # perfect pitch
        result_full = self.service.score(dev, confidence=1.0)
        result_half = self.service.score(dev, confidence=0.5)
        assert result_full.weighted_total() == 100.0
        assert result_half.weighted_total() == pytest.approx(75.0, rel=0.01)  # 100×0.75

    # ---- Style weights ----

    def test_pop_weights(self):
        """Pop: pitch=0.40, rhythm=0.30, volume=0.15, breath=0.15"""
        dev = DeviationData()
        result = self.service.score(dev, style="pop", confidence=1.0)
        # All 100 → weighted = 100
        assert result.weighted_total() == 100.0

    def test_classical_higher_pitch_weight(self):
        """Classical: pitch=0.50, 音准权重更高"""
        dev = DeviationData(avg_pitch_cents=50.0)  # 75 pitch, everything else 100
        pop_result = self.service.score(dev, style="pop", confidence=1.0)
        classical_result = self.service.score(dev, style="classical", confidence=1.0)
        # Classical 音准权重大 → 受 pitch 影响更大 → 总分更低
        assert classical_result.weighted_total() < pop_result.weighted_total()

    # ---- Suggestions ----
    # v7.19 E5: generate_suggestions 已从 domain 层移除 (建议复用 DDD AdviceGenerator,
    # 由 CompareAudioUseCase.execute_lightweight 编排) — 契约见 test_compare_audio_advice.py
