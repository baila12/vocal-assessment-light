"""
P1-5 (审查 6.1 M1/M2 + 6.3): 50.0 假分 fallback 标记

设计启发式维度 (muscle_strength/timbre) 恒 is_heuristic=True;
v7.16 P2-15: 死 calculate() 路径 (含静默 50.0 fallback) 已移除 —
唯一生产路径 calculate_ddd() 无静默 fallback (失败直接冒泡, 可观测),
故 fallback 打标测试随死路径删除。本文件保留:
- 值对象 is_heuristic 默认值契约 (设计启发式 vs 普通维度)
- calculate_ddd 的 scoring_warnings 字段契约 (恒空)
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
    """calculate_ddd() 唯一生产路径的 scoring_warnings 契约"""

    def test_calculate_ddd_has_empty_scoring_warnings_field(self):
        """calculate_ddd 也带 scoring_warnings 字段 (下游 _s() 读取)"""
        orch = ScoringOrchestrator()
        result = orch.calculate_ddd()  # 全 None → 各维度 0.0
        assert result["scoring_warnings"] == []
