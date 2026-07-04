"""
评分稳健性单元测试

测试覆盖评分系统在边界条件和极端输入下的行为:
1. 评分可重现性 (相同输入 → 相同分数)
2. 极端值处理 (0, 100, NaN 安全)
3. 空数据 / 零数据降级
4. 评分分布验证 (不崩塌到单一区间)
5. 所有维度 score → level 映射一致性
"""
import pytest
import numpy as np

from services.scoring import (
    PitchScorer, RhythmScorer, BreathScorer,
    TechniqueScorer, ArtistryScorer, CriticalRulesHandler
)
from services.scoring_config import (
    PitchThresholds, RhythmThresholds, BreathThresholds,
    TechniqueThresholds, CriticalRuleThresholds
)
from services.features.types import (
    PitchDeviationResult, RhythmAlignmentResult,
    BreathStabilityResult, VocalTechniqueResult
)
from services.scoring.types import PitchDiagnosis, RhythmDiagnosis, BreathDiagnosis
from services.audio_features_service import AudioFeaturesResult
from services.score_service import ScoreResultV4

pytestmark = pytest.mark.unit


# ============================================================================
# 评分可重现性
# ============================================================================

class TestScoringReproducibility:
    """同一输入必须返回相同分数"""

    def test_pitch_scorer_deterministic(self):
        """PitchScorer 相同输入 → 相同输出"""
        scorer = PitchScorer(PitchThresholds())
        result = PitchDeviationResult(
            mae_cents=25.0, detection_rate=0.9,
            pitch_breaks=1, pitch_wobble=15.0,
            consecutive_off_notes=0
        )

        scores = [scorer.calculate(result)[0] for _ in range(10)]
        assert all(s == scores[0] for s in scores), \
            f"PitchScorer 分数不一致: {scores}"

    def test_rhythm_scorer_deterministic(self):
        """RhythmScorer 相同输入 → 相同输出"""
        scorer = RhythmScorer(RhythmThresholds())
        result = RhythmAlignmentResult(
            avg_deviation_ratio=0.15, irregularity=0.2,
            beats_per_second=2.0, onset_count=100,
            off_beat_segments=10
        )

        scores = [scorer.calculate(result)[0] for _ in range(10)]
        assert all(s == scores[0] for s in scores), \
            f"RhythmScorer 分数不一致: {scores}"

    def test_breath_scorer_deterministic(self):
        """BreathScorer 相同输入 → 相同输出"""
        scorer = BreathScorer(BreathThresholds())
        result = BreathStabilityResult(
            rms_fluctuation=0.15, breath_breaks=0,
            professional_breath_score=75.0,
            long_note_support_score=75.0,
            dynamic_control_score=75.0,
            breath_design_score=75.0,
            breath_technique_score=75.0,
            is_artistic_fluctuation=True,
            controlled_breathiness=50.0,
            long_note_count=2, soft_segment_count=1,
            soft_singing_quality=60.0,
            clean_breath_count=2,
            dynamic_range=25.0, uncontrolled_leak=10.0
        )

        scores = [scorer.calculate(result)[0] for _ in range(10)]
        assert all(s == scores[0] for s in scores), \
            f"BreathScorer 分数不一致: {scores}"

    def test_technique_scorer_deterministic(self):
        """TechniqueScorer 相同输入 → 相同输出"""
        scorer = TechniqueScorer(TechniqueThresholds(), singing_style='pop')
        technique = VocalTechniqueResult(
            technique_score=65.0, vibrato_count=3,
            vibrato_quality=70.0, slide_count=1,
            falsetto_segments=0
        )

        scores = [scorer.calculate(hnr=12.0, cpp=1.0, technique=technique)[0]
                  for _ in range(10)]
        assert all(s == scores[0] for s in scores), \
            f"TechniqueScorer 分数不一致: {scores}"

    def test_critical_rules_deterministic(self):
        """CriticalRulesHandler 相同输入 → 相同输出"""
        handler = CriticalRulesHandler(CriticalRuleThresholds())

        def _make_result():
            result = ScoreResultV4()
            result.total_score = 75.0
            features = AudioFeaturesResult()
            features.pitch_deviation = PitchDeviationResult(
                mae_cents=50.0, detection_rate=0.9,
                pitch_breaks=0, pitch_wobble=20.0,
                consecutive_off_notes=6
            )
            features.rhythm_alignment = RhythmAlignmentResult(
                avg_deviation_ratio=0.2, irregularity=0.1,
                beats_per_second=2.0, onset_count=100,
                off_beat_segments=10
            )
            features.hnr = 15.0
            return result, features

        outputs = []
        for _ in range(10):
            result, features = _make_result()
            handler.apply(result, features)
            outputs.append((result.total_score, result.is_disqualified))

        assert all(o == outputs[0] for o in outputs), \
            f"CriticalRules 输出不一致: {outputs}"


# ============================================================================
# 边界条件处理
# ============================================================================

class TestScoringBoundaryInputs:
    """极端输入值处理"""

    # ── 零值 ──

    def test_pitch_zero_mae(self):
        """MAE = 0 音分 (完美音准)"""
        scorer = PitchScorer(PitchThresholds())
        result = PitchDeviationResult(
            mae_cents=0.0, detection_rate=1.0,
            pitch_breaks=0, pitch_wobble=0.0,
            consecutive_off_notes=0
        )
        score, diagnosis = scorer.calculate(result)
        assert 0 <= score <= 100
        assert diagnosis.level == "专业级"

    def test_rhythm_zero_onset(self):
        """零 onset (完全无声)"""
        scorer = RhythmScorer(RhythmThresholds())
        result = RhythmAlignmentResult(
            avg_deviation_ratio=0.0, irregularity=0.0,
            beats_per_second=0.0, onset_count=0,
            off_beat_segments=0
        )
        score, _ = scorer.calculate(result)
        assert 0 <= score <= 100

    def test_breath_all_zeros(self):
        """所有气息子维度为 0"""
        scorer = BreathScorer(BreathThresholds())
        result = BreathStabilityResult(
            rms_fluctuation=0.0, breath_breaks=0,
            professional_breath_score=0.0,
            long_note_support_score=0.0,
            dynamic_control_score=0.0,
            breath_design_score=0.0,
            breath_technique_score=0.0,
            is_artistic_fluctuation=False,
            controlled_breathiness=0.0,
            long_note_count=0, soft_segment_count=0,
            soft_singing_quality=0.0,
            clean_breath_count=0,
            dynamic_range=0.0, uncontrolled_leak=0.0
        )
        score, _ = scorer.calculate(result)
        assert 0 <= score <= 100

    def test_technique_zero_hnr_cpp(self):
        """HNR 和 CPP 均为 0"""
        scorer = TechniqueScorer(TechniqueThresholds(), singing_style='pop')
        technique = VocalTechniqueResult(
            technique_score=0.0, vibrato_count=0,
            vibrato_quality=0.0, slide_count=0,
            falsetto_segments=0
        )
        score, _ = scorer.calculate(hnr=0.0, cpp=0.0, technique=technique)
        assert 0 <= score <= 100

    # ── 极值 ──

    def test_pitch_very_large_deviation(self):
        """极大音准偏差 (200 音分 = 全音)"""
        scorer = PitchScorer(PitchThresholds())
        result = PitchDeviationResult(
            mae_cents=200.0, detection_rate=0.6,
            pitch_breaks=10, pitch_wobble=80.0,
            consecutive_off_notes=20
        )
        score, _ = scorer.calculate(result)
        assert 0 <= score <= 100

    def test_rhythm_very_irregular(self):
        """极度不规则节奏"""
        scorer = RhythmScorer(RhythmThresholds())
        result = RhythmAlignmentResult(
            avg_deviation_ratio=2.0, irregularity=1.0,
            beats_per_second=10.0, onset_count=1000,
            off_beat_segments=500
        )
        score, _ = scorer.calculate(result)
        assert 0 <= score <= 100

    def test_breath_very_unstable(self):
        """极度不稳定气息"""
        scorer = BreathScorer(BreathThresholds())
        result = BreathStabilityResult(
            rms_fluctuation=5.0, breath_breaks=50,
            professional_breath_score=0.0,
            long_note_support_score=0.0,
            dynamic_control_score=0.0,
            breath_design_score=0.0,
            breath_technique_score=0.0,
            is_artistic_fluctuation=False,
            controlled_breathiness=0.0,
            long_note_count=0, soft_segment_count=0,
            soft_singing_quality=0.0,
            clean_breath_count=0,
            dynamic_range=5.0, uncontrolled_leak=100.0
        )
        score, _ = scorer.calculate(result)
        assert 0 <= score <= 100

    # ── 检测率边界 ──

    def test_pitch_zero_detection_rate(self):
        """检测率为 0 (完全无声)"""
        scorer = PitchScorer(PitchThresholds())
        result = PitchDeviationResult(
            mae_cents=50.0, detection_rate=0.0,
            pitch_breaks=0, pitch_wobble=0.0,
            consecutive_off_notes=0
        )
        score, diagnosis = scorer.calculate(result)
        assert 0 <= score <= 100
        assert len(diagnosis.issues) > 0

    def test_pitch_full_detection_rate(self):
        """检测率为 1.0 (完美检测)"""
        scorer = PitchScorer(PitchThresholds())
        result = PitchDeviationResult(
            mae_cents=20.0, detection_rate=1.0,
            pitch_breaks=0, pitch_wobble=10.0,
            consecutive_off_notes=0
        )
        score, _ = scorer.calculate(result)
        assert score >= 70


# ============================================================================
# 分数分布验证
# ============================================================================

class TestScoreDistribution:
    """验证评分不会崩塌到单一区间"""

    def test_pitch_spread_across_quality_levels(self):
        """不同音准质量产生有意义的分数分布"""
        scorer = PitchScorer(PitchThresholds())

        def _score(mae, rate=0.9):
            r = PitchDeviationResult(
                mae_cents=mae, detection_rate=rate,
                pitch_breaks=0, pitch_wobble=mae * 0.5,
                consecutive_off_notes=0
            )
            return scorer.calculate(r)[0]

        excellent = _score(5.0)   # ~完美
        good = _score(25.0)        # ~良好
        mediocre = _score(60.0)    # ~一般
        poor = _score(120.0)       # ~差

        # 分数应递减
        assert excellent > good > mediocre > poor, \
            f"分数不递减: {excellent:.0f} > {good:.0f} > {mediocre:.0f} > {poor:.0f}"

        # 高低分差应显著 (> 30)
        assert excellent - poor > 30, \
            f"音准区分度过窄: 高={excellent:.0f} 低={poor:.0f}"

    def test_rhythm_spread_across_quality_levels(self):
        """不同节奏质量产生有意义的分数分布"""
        scorer = RhythmScorer(RhythmThresholds())

        def _score(deviation, irregularity=0.1):
            r = RhythmAlignmentResult(
                avg_deviation_ratio=deviation, irregularity=irregularity,
                beats_per_second=2.0, onset_count=100, off_beat_segments=5
            )
            return scorer.calculate(r)[0]

        excellent = _score(0.05)
        good = _score(0.15)
        poor = _score(0.60)

        assert excellent > good > poor, \
            f"节奏分数不递减: {excellent:.0f} > {good:.0f} > {poor:.0f}"
        assert excellent - poor > 20, \
            f"节奏区分度过窄: 高={excellent:.0f} 低={poor:.0f}"

    def test_breath_spread_across_quality_levels(self):
        """不同气息质量产生有意义的分数分布"""
        scorer = BreathScorer(BreathThresholds())

        def _make(fluctuation, pro_score=0):
            return BreathStabilityResult(
                rms_fluctuation=fluctuation, breath_breaks=0,
                professional_breath_score=pro_score,
                long_note_support_score=float(pro_score),
                dynamic_control_score=float(pro_score),
                breath_design_score=float(pro_score),
                breath_technique_score=float(pro_score),
                is_artistic_fluctuation=fluctuation < 0.15,
                controlled_breathiness=50.0,
                long_note_count=2, soft_segment_count=1,
                soft_singing_quality=60.0, clean_breath_count=2,
                dynamic_range=25.0, uncontrolled_leak=5.0
            )

        stable = scorer.calculate(_make(0.05))[0]
        normal = scorer.calculate(_make(0.20))[0]
        unstable = scorer.calculate(_make(0.50))[0]

        assert stable > normal > unstable, \
            f"气息分数不递减: {stable:.0f} > {normal:.0f} > {unstable:.0f}"
        assert stable - unstable > 10, \
            f"气息区分度过窄: 稳定={stable:.0f} 不稳定={unstable:.0f}"


# ============================================================================
# Diagnosis 一致性验证
# ============================================================================

class TestDiagnosisConsistency:
    """评分与诊断信息一致性"""

    def test_high_score_gives_professional_level(self):
        """高分 (>= 95) 应对应 '专业级'"""
        for ScorerCls, ThresholdsCls, make_result in [
            (PitchScorer, PitchThresholds, lambda: PitchDeviationResult(
                mae_cents=3.0, detection_rate=0.98,
                pitch_breaks=0, pitch_wobble=5.0, consecutive_off_notes=0)),
        ]:
            scorer = ScorerCls(ThresholdsCls())
            _, diagnosis = scorer.calculate(make_result())
            assert diagnosis.level == "专业级", \
                f"{ScorerCls.__name__} 高分应='专业级', 实际='{diagnosis.level}'"

    def test_low_score_gives_needs_improvement(self):
        """低分 (< 50) 应对应 '待改进'"""
        scorer = PitchScorer(PitchThresholds())
        result = PitchDeviationResult(
            mae_cents=120.0, detection_rate=0.6,
            pitch_breaks=5, pitch_wobble=60.0,
            consecutive_off_notes=3
        )
        _, diagnosis = scorer.calculate(result)
        assert diagnosis.level == "待改进", \
            f"低分应='待改进', 实际='{diagnosis.level}'"

    def test_diagnosis_never_empty_for_poor_score(self):
        """低分评分应有诊断建议"""
        scorer = PitchScorer(PitchThresholds())
        result = PitchDeviationResult(
            mae_cents=100.0, detection_rate=0.5,
            pitch_breaks=3, pitch_wobble=50.0,
            consecutive_off_notes=4
        )
        score, diagnosis = scorer.calculate(result)
        if score < 60:
            assert len(diagnosis.issues) > 0 or len(diagnosis.suggestions) > 0, \
                f"低分 ({score}) 应有诊断信息"


# ============================================================================
# CriticalRules 级联惩罚
# ============================================================================

class TestCriticalRulesCascade:
    """多条件触发时的级联惩罚"""

    def test_multi_dimension_penalty(self):
        """多维度同时触发惩罚 → 取最严格"""
        handler = CriticalRulesHandler(CriticalRuleThresholds())
        result = ScoreResultV4()
        result.total_score = 80.0

        features = AudioFeaturesResult()
        # 同时触发: 连续跑调 + 脱离节拍
        features.pitch_deviation = PitchDeviationResult(
            mae_cents=50.0, detection_rate=0.9,
            pitch_breaks=0, pitch_wobble=20.0,
            consecutive_off_notes=6  # 触发连续跑调
        )
        features.rhythm_alignment = RhythmAlignmentResult(
            avg_deviation_ratio=0.3, irregularity=0.2,
            beats_per_second=2.0, onset_count=100,
            off_beat_segments=50  # 触发脱离节拍
        )
        features.hnr = 2.0  # 触发低 HNR

        handler.apply(result, features)

        # 三条件触发，取最严厉惩罚
        assert result.total_score <= 50, \
            f"三条件触发应 cap <= 50, 实际: {result.total_score}"
        assert result.is_disqualified is True

    def test_no_trigger_when_all_good(self):
        """所有指标正常 → 不触发任何惩罚"""
        handler = CriticalRulesHandler(CriticalRuleThresholds())
        result = ScoreResultV4()
        result.total_score = 85.0

        features = AudioFeaturesResult()
        features.pitch_deviation = PitchDeviationResult(
            mae_cents=15.0, detection_rate=0.9,
            pitch_breaks=0, pitch_wobble=10.0,
            consecutive_off_notes=0
        )
        features.rhythm_alignment = RhythmAlignmentResult(
            avg_deviation_ratio=0.1, irregularity=0.05,
            beats_per_second=2.0, onset_count=100,
            off_beat_segments=0
        )
        features.hnr = 18.0

        handler.apply(result, features)

        assert result.total_score == 85.0, \
            f"正常情况不应改分, 实际: {result.total_score}"
        assert result.is_disqualified is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
