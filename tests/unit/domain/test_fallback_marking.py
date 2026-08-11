"""
P1-5 (审查 6.1 M1/M2 + 6.3): 50.0 假分 fallback 标记

设计启发式维度 (muscle_strength/timbre) 恒 is_heuristic=True;
评分失败 fallback 时, 其余维度也打 is_heuristic=True, 并在
scoring_warnings 中透出, 避免"假 50.0"伪装成真实平庸分数。
"""

from backend.application.assessment.scoring_orchestrator import ScoringOrchestrator
from backend.domain.assessment.value_objects import (
    PitchScore, RhythmScore, BreathScore, TechniqueScore, ArtistryScore,
    MuscleStrengthScore, TimbreAdjustment,
)


class TestValueObjectHeuristicFlag:
    """5 个普通维度默认 is_heuristic=False; 2 个设计启发式默认 True"""

    def test_pitch_default_not_heuristic(self):
        s = PitchScore(raw_score=80.0, mae_cents=30, rpa=0.5, rca=0.5,
                       gross_error_rate=0.1, octave_error_rate=0.0,
                       smoothness_cv=1.0, detection_rate=0.9, pitch_breaks=0)
        assert s.is_heuristic is False

    def test_rhythm_default_not_heuristic(self):
        s = RhythmScore(raw_score=80.0, onset_cv=0.3, median_ioi_deviation=0.05,
                        irregularity_penalty=0.0, is_clean_vocal=True)
        assert s.is_heuristic is False

    def test_breath_default_not_heuristic(self):
        s = BreathScore(raw_score=80.0, long_note_support=0.8, dynamic_control=0.7,
                        breath_design=0.6, breath_technique=0.7, is_clean_vocal=True)
        assert s.is_heuristic is False

    def test_technique_default_not_heuristic(self):
        s = TechniqueScore(raw_score=80.0, articulation_clarity=0.7, breath_voice_ratio=0.5)
        assert s.is_heuristic is False

    def test_artistry_default_not_heuristic(self):
        s = ArtistryScore(raw_score=80.0, vibrato_quality=0.6, dynamic_control=0.7,
                          phrase_expression=0.6, pitch_variation=0.5)
        assert s.is_heuristic is False

    def test_muscle_is_design_heuristic(self):
        s = MuscleStrengthScore(raw_score=80.0, body_muscle_strength=0.7,
                                facial_muscle_strength=0.7)
        assert s.is_heuristic is True

    def test_timbre_is_design_heuristic(self):
        s = TimbreAdjustment(adjustment=1.0, brightness_score=0.5, warmth_score=0.5,
                             nasality_score=0.0, confidence=0.8)
        assert s.is_heuristic is True


class TestScoringOrchestratorFallback:
    """评分失败时 fallback 打标记 + calculate() 收集 scoring_warnings"""

    @staticmethod
    def _boom(*args, **kwargs):
        raise ValueError("simulated scorer failure")

    def test_score_pitch_fallback_marks_heuristic(self, monkeypatch):
        """PitchScorer 抛异常 → PitchScore(is_heuristic=True, raw=50.0)"""
        orch = ScoringOrchestrator()
        monkeypatch.setattr(orch._pitch_scorer, "calculate", self._boom)
        score = orch._score_pitch(object())
        assert score.raw_score == 50.0
        assert score.is_heuristic is True

    def test_calculate_collects_all_fallback_warnings(self, monkeypatch):
        """5 个非设计启发式维度全失败 → scoring_warnings 有 5 条, 不含 muscle/timbre"""
        orch = ScoringOrchestrator()
        for name in ("_pitch_scorer", "_rhythm_scorer", "_breath_scorer",
                     "_technique_scorer", "_artistry_scorer"):
            monkeypatch.setattr(getattr(orch, name), "calculate", self._boom)

        result = orch.calculate(object(), is_clean_vocal=False)

        warnings = result["scoring_warnings"]
        assert isinstance(warnings, list)
        assert len(warnings) == 5, f"应有 5 条维度失败告警, 实际 {warnings}"
        # 设计启发式维度 (muscle/timbre) 不产生失败告警
        assert set(result["heuristic_dimensions"]) == {"muscle_strength", "timbre"}
        # 每条告警可读, 含维度名
        for w in warnings:
            assert isinstance(w, str) and w

    def test_calculate_no_fallback_no_warnings(self, monkeypatch):
        """正常评分路径 → scoring_warnings 为空"""
        orch = ScoringOrchestrator()
        # 用真实 features (PitchFeatures() 等空默认) 走 calculate 适配器路径
        class _F:
            pitch_deviation = None
            rhythm_info = None
            breath_stability = None
            technique_info = None
            muscle_features = None
            artistry_info = None
        result = orch.calculate(_F(), is_clean_vocal=False)
        assert result["scoring_warnings"] == []

    def test_calculate_ddd_has_empty_scoring_warnings_field(self):
        """calculate_ddd 也带 scoring_warnings 字段 (下游 _s() 读取)"""
        orch = ScoringOrchestrator()
        result = orch.calculate_ddd()  # 全 None → 各维度 0.0
        assert result["scoring_warnings"] == []
