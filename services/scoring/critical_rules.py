"""
底线规则处理器

负责应用评分底线规则（一票否决机制）
"""
import logging

from services.audio_features_service import AudioFeaturesResult
from services.scoring import ScoreResultV4
from services.scoring_config import CriticalRuleThresholds

logger = logging.getLogger(__name__)


class CriticalRulesHandler:
    """
    底线规则处理器

    规则：
    1. 连续超过阈值个音符跑调超半音 → 扣20分
    2. 严重脱离节拍(比例超过阈值) → 上限70分
    3. 严重漏气/破音 → 不合格
    """

    def __init__(self, thresholds: CriticalRuleThresholds):
        """
        初始化底线规则处理器

        Args:
            thresholds: 底线规则阈值配置
        """
        self.thresholds = thresholds

    def apply(
        self,
        result: ScoreResultV4,
        features: AudioFeaturesResult
    ) -> None:
        """
        应用底线规则

        Args:
            result: 评分结果（会被修改）
            features: 音频特征分析结果
        """
        # 规则1：连续跑调
        if self.thresholds.should_apply_pitch_penalty(
            features.pitch_deviation.consecutive_off_notes
        ):
            result.total_score = max(0, result.total_score - 20)
            result.critical_issues.append(
                f"连续{features.pitch_deviation.consecutive_off_notes}个音符跑调，扣20分"
            )
            result.is_disqualified = True

        # 规则2：脱离节拍
        if features.rhythm_alignment.onset_count > 0:
            off_beat_ratio = (
                features.rhythm_alignment.off_beat_segments /
                features.rhythm_alignment.onset_count
            )
            if self.thresholds.should_apply_rhythm_penalty(off_beat_ratio):
                result.total_score = min(result.total_score, 70)
                result.critical_issues.append(
                    f"脱离节拍比例过高({off_beat_ratio:.0%})，总分上限70分"
                )
                result.is_disqualified = True

        # 规则3：严重漏气
        if self.thresholds.should_apply_quality_penalty(features.hnr):
            result.total_score = min(result.total_score, 50)
            result.critical_issues.append("HNR过低（严重漏气），总分上限50分")
            result.is_disqualified = True
