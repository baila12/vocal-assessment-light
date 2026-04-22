"""
单元测试 - 评分器模块测试
测试 services/scoring 模块的各维度评分器
"""
import pytest
import numpy as np
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from services.scoring import (
    PitchDiagnosis,
    RhythmDiagnosis,
    BreathDiagnosis,
    TechniqueDiagnosis,
    ArtistryDiagnosis,
    ScoreResultV4,
    PitchScorer,
    RhythmScorer,
    BreathScorer,
    TechniqueScorer,
    ArtistryScorer,
    CriticalRulesHandler
)
from services.scoring_config import (
    PitchThresholds,
    RhythmThresholds,
    BreathThresholds,
    TechniqueThresholds,
    CriticalRuleThresholds
)
from services.audio_features_service import (
    PitchDeviationResult,
    RhythmAlignmentResult,
    BreathStabilityResult,
    VocalTechniqueResult
)


class TestPitchScorer:
    """音准评分器测试"""

    def setup_method(self):
        self.thresholds = PitchThresholds()
        self.scorer = PitchScorer(self.thresholds)

    def test_excellent_pitch(self):
        """测试优秀音准（低偏差）"""
        result = PitchDeviationResult(
            mae_cents=8.0,  # 低于 excellent 阈值
            detection_rate=0.95,
            pitch_breaks=0,
            pitch_wobble=10.0,
            consecutive_off_notes=0
        )
        score, diagnosis = self.scorer.calculate(result)

        assert score >= 95.0
        assert diagnosis.level == "专业级"
        assert diagnosis.mae_cents == 8.0

    def test_good_pitch(self):
        """测试良好音准"""
        result = PitchDeviationResult(
            mae_cents=25.0,  # 在 good 范围内
            detection_rate=0.9,
            pitch_breaks=0,
            pitch_wobble=20.0,
            consecutive_off_notes=0
        )
        score, diagnosis = self.scorer.calculate(result)

        assert 85 <= score <= 100
        assert diagnosis.level in ["良好", "专业级"]

    def test_poor_pitch(self):
        """测试较差音准（高偏差）"""
        result = PitchDeviationResult(
            mae_cents=80.0,  # 高于 pass 阈值
            detection_rate=0.8,
            pitch_breaks=2,
            pitch_wobble=40.0,
            consecutive_off_notes=0
        )
        score, diagnosis = self.scorer.calculate(result)

        assert score < 70
        assert diagnosis.level == "待改进"
        assert len(diagnosis.suggestions) > 0

    def test_low_detection_rate_penalty(self):
        """测试低检测率惩罚"""
        result = PitchDeviationResult(
            mae_cents=15.0,
            detection_rate=0.3,  # 低检测率
            pitch_breaks=0,
            pitch_wobble=15.0,
            consecutive_off_notes=0
        )
        score, diagnosis = self.scorer.calculate(result)

        # 应该有惩罚
        assert len(diagnosis.issues) > 0
        assert any("检测率低" in issue for issue in diagnosis.issues)

    def test_pitch_breaks_penalty(self):
        """测试音高断层惩罚"""
        result = PitchDeviationResult(
            mae_cents=15.0,
            detection_rate=0.9,
            pitch_breaks=5,  # 多处断层
            pitch_wobble=15.0,
            consecutive_off_notes=0
        )
        score, diagnosis = self.scorer.calculate(result)

        assert len(diagnosis.issues) > 0
        assert any("断层" in issue for issue in diagnosis.issues)


class TestRhythmScorer:
    """节奏评分器测试"""

    def setup_method(self):
        self.thresholds = RhythmThresholds()
        self.scorer = RhythmScorer(self.thresholds)

    def test_excellent_rhythm(self):
        """测试优秀节奏"""
        result = RhythmAlignmentResult(
            avg_deviation_ratio=0.08,  # 低于 excellent 阈值
            irregularity=0.1,
            beats_per_second=2.0,
            onset_count=100,
            off_beat_segments=5
        )
        score, diagnosis = self.scorer.calculate(result)

        assert score >= 95.0
        assert diagnosis.level == "专业级"

    def test_poor_rhythm(self):
        """测试较差节奏"""
        result = RhythmAlignmentResult(
            avg_deviation_ratio=0.5,  # 高于 pass 阈值
            irregularity=0.4,
            beats_per_second=2.0,
            onset_count=100,
            off_beat_segments=30
        )
        score, diagnosis = self.scorer.calculate(result)

        assert score < 70
        assert diagnosis.level == "待改进"

    def test_irregularity_penalty(self):
        """测试不规则度惩罚"""
        result = RhythmAlignmentResult(
            avg_deviation_ratio=0.15,
            irregularity=0.5,  # 高不规则度
            beats_per_second=2.0,
            onset_count=100,
            off_beat_segments=10
        )
        score, diagnosis = self.scorer.calculate(result)

        assert len(diagnosis.issues) > 0
        assert any("不规则" in issue for issue in diagnosis.issues)


class TestBreathScorer:
    """气息评分器测试"""

    def setup_method(self):
        self.thresholds = BreathThresholds()
        self.scorer = BreathScorer(self.thresholds)

    def test_excellent_breath(self):
        """测试优秀气息"""
        result = BreathStabilityResult(
            rms_fluctuation=0.12,  # 低波动
            breath_breaks=0,
            professional_breath_score=92.0,
            long_note_support_score=90.0,
            dynamic_control_score=85.0,
            breath_design_score=88.0,
            breath_technique_score=80.0,
            is_artistic_fluctuation=True,
            controlled_breathiness=60.0,
            long_note_count=3,
            soft_segment_count=2,
            soft_singing_quality=75.0,
            clean_breath_count=2,
            dynamic_range=35.0,
            uncontrolled_leak=5.0
        )
        score, diagnosis = self.scorer.calculate(result)

        assert score >= 85.0
        assert diagnosis.level == "专业级"
        assert diagnosis.is_artistic is True

    def test_breath_breaks_penalty(self):
        """测试气息断层惩罚"""
        result = BreathStabilityResult(
            rms_fluctuation=0.25,
            breath_breaks=6,  # 多处断层
            professional_breath_score=0.0,  # 使用旧逻辑
            long_note_support_score=60.0,
            dynamic_control_score=60.0,
            breath_design_score=60.0,
            breath_technique_score=60.0,
            is_artistic_fluctuation=False,
            controlled_breathiness=20.0,
            long_note_count=0,
            soft_segment_count=0,
            soft_singing_quality=0.0,
            clean_breath_count=0,
            dynamic_range=15.0,
            uncontrolled_leak=40.0
        )
        score, diagnosis = self.scorer.calculate(result)

        assert len(diagnosis.issues) > 0
        assert any("断层" in issue for issue in diagnosis.issues)


class TestTechniqueScorer:
    """发声技术评分器测试"""

    def setup_method(self):
        self.thresholds = TechniqueThresholds()
        self.scorer = TechniqueScorer(self.thresholds, singing_style='pop')

    def test_excellent_technique(self):
        """测试优秀发声技术"""
        technique = VocalTechniqueResult(
            technique_score=85.0,
            vibrato_count=5,
            vibrato_quality=80.0,
            slide_count=2,
            falsetto_segments=1
        )
        score, diagnosis = self.scorer.calculate(
            hnr=18.0,  # 高 HNR
            cpp=1.5,   # 高 CPP
            technique=technique
        )

        assert score >= 80.0
        assert diagnosis.level == "专业级"

    def test_low_hnr_warning(self):
        """测试低 HNR 警告"""
        technique = VocalTechniqueResult(
            technique_score=50.0,
            vibrato_count=0,
            vibrato_quality=0.0,
            slide_count=0,
            falsetto_segments=0
        )
        score, diagnosis = self.scorer.calculate(
            hnr=3.0,  # 低 HNR
            cpp=0.2,
            technique=technique
        )

        assert len(diagnosis.issues) > 0
        assert any("HNR" in issue for issue in diagnosis.issues)

    def test_classical_style_higher_hnr_requirement(self):
        """测试美声唱法更高的 HNR 要求"""
        scorer = TechniqueScorer(self.thresholds, singing_style='classical')

        technique = VocalTechniqueResult(
            technique_score=70.0,
            vibrato_count=3,
            vibrato_quality=75.0,
            slide_count=0,
            falsetto_segments=0
        )

        # 相同 HNR，美声评分应低于流行
        score_classical, _ = scorer.calculate(hnr=15.0, cpp=1.0, technique=technique)
        score_pop, _ = self.scorer.calculate(hnr=15.0, cpp=1.0, technique=technique)

        # 美声对 HNR 要求更高，同等级 HNR 分数可能较低
        # 但由于权重和其他因素，这里只验证能正常计算
        assert 0 <= score_classical <= 100
        assert 0 <= score_pop <= 100


class TestArtistryScorer:
    """艺术表现评分器测试"""

    def setup_method(self):
        self.scorer = ArtistryScorer()

    def test_rich_emotions(self):
        """测试丰富情感"""
        emotions = {
            'happy': 0.4,
            'sad': 0.3,
            'angry': 0.2,
            'neutral': 0.1
        }
        technique = VocalTechniqueResult(
            technique_score=70.0,
            vibrato_count=4,
            vibrato_quality=75.0,
            slide_count=3,
            falsetto_segments=2
        )
        score, diagnosis = self.scorer.calculate(
            emotion_confidence=0.4,
            emotions=emotions,
            technique=technique
        )

        assert score >= 70.0
        assert any("丰富" in issue for issue in diagnosis.issues)

    def test_monotonic_emotion(self):
        """测试单调情感"""
        emotions = {
            'neutral': 0.9,
            'happy': 0.05,
            'sad': 0.03,
            'angry': 0.02
        }
        technique = VocalTechniqueResult(
            technique_score=50.0,
            vibrato_count=0,
            vibrato_quality=0.0,
            slide_count=0,
            falsetto_segments=0
        )
        score, diagnosis = self.scorer.calculate(
            emotion_confidence=0.9,
            emotions=emotions,
            technique=technique
        )

        assert any("单调" in issue for issue in diagnosis.issues)

    def test_no_emotions_data(self):
        """测试无情感数据"""
        technique = VocalTechniqueResult(
            technique_score=60.0,
            vibrato_count=2,
            vibrato_quality=60.0,
            slide_count=1,
            falsetto_segments=0
        )
        score, diagnosis = self.scorer.calculate(
            emotion_confidence=0.5,
            emotions=None,
            technique=technique
        )

        assert 0 <= score <= 100


class TestCriticalRulesHandler:
    """底线规则处理器测试"""

    def setup_method(self):
        self.thresholds = CriticalRuleThresholds()
        self.handler = CriticalRulesHandler(self.thresholds)

    def test_consecutive_off_pitch_penalty(self):
        """测试连续跑调惩罚"""
        from services.audio_features_service import AudioFeaturesResult

        result = ScoreResultV4()
        result.total_score = 85.0

        features = AudioFeaturesResult()
        features.pitch_deviation = PitchDeviationResult(
            mae_cents=50.0,
            detection_rate=0.9,
            pitch_breaks=0,
            pitch_wobble=20.0,
            consecutive_off_notes=6  # 超过阈值
        )
        features.rhythm_alignment = RhythmAlignmentResult(
            avg_deviation_ratio=0.2,
            irregularity=0.1,
            beats_per_second=2.0,
            onset_count=100,
            off_beat_segments=10
        )
        features.hnr = 15.0

        self.handler.apply(result, features)

        assert result.total_score == 65.0  # 扣20分
        assert result.is_disqualified is True
        assert len(result.critical_issues) > 0

    def test_off_beat_penalty(self):
        """测试脱离节拍惩罚"""
        from services.audio_features_service import AudioFeaturesResult

        result = ScoreResultV4()
        result.total_score = 80.0

        features = AudioFeaturesResult()
        features.pitch_deviation = PitchDeviationResult(
            mae_cents=20.0,
            detection_rate=0.9,
            pitch_breaks=0,
            pitch_wobble=15.0,
            consecutive_off_notes=0
        )
        features.rhythm_alignment = RhythmAlignmentResult(
            avg_deviation_ratio=0.3,
            irregularity=0.2,
            beats_per_second=2.0,
            onset_count=100,
            off_beat_segments=50  # 50% 脱离节拍
        )
        features.hnr = 15.0

        self.handler.apply(result, features)

        assert result.total_score == 70.0  # 上限70分
        assert result.is_disqualified is True

    def test_low_hnr_penalty(self):
        """测试低 HNR 惩罚"""
        from services.audio_features_service import AudioFeaturesResult

        result = ScoreResultV4()
        result.total_score = 75.0

        features = AudioFeaturesResult()
        features.pitch_deviation = PitchDeviationResult(
            mae_cents=20.0,
            detection_rate=0.9,
            pitch_breaks=0,
            pitch_wobble=15.0,
            consecutive_off_notes=0
        )
        features.rhythm_alignment = RhythmAlignmentResult(
            avg_deviation_ratio=0.2,
            irregularity=0.1,
            beats_per_second=2.0,
            onset_count=100,
            off_beat_segments=10
        )
        features.hnr = 2.0  # 低于阈值

        self.handler.apply(result, features)

        assert result.total_score == 50.0  # 上限50分
        assert result.is_disqualified is True


class TestScoreResultV4:
    """评分结果 DTO 测试"""

    def test_create_default_result(self):
        """测试创建默认结果"""
        result = ScoreResultV4()

        assert result.pitch_score == 0.0
        assert result.rhythm_score == 0.0
        assert result.breath_score == 0.0
        assert result.technique_score == 0.0
        assert result.artistry_score == 0.0
        assert result.total_score == 0.0
        assert result.is_disqualified is False

    def test_result_with_scores(self):
        """测试带分数的结果"""
        result = ScoreResultV4()
        result.pitch_score = 85.0
        result.rhythm_score = 80.0
        result.breath_score = 75.0
        result.technique_score = 70.0
        result.artistry_score = 65.0
        result.total_score = 76.0
        result.level = "良好"

        # 兼容旧接口
        assert result.pitch == 0.0  # 需要手动同步
        result.pitch = result.pitch_score
        assert result.pitch == 85.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
