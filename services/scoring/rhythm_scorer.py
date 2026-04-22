"""
节奏评分器

负责节奏维度的评分计算和诊断生成
"""
from typing import Tuple
import logging

from services.audio_features_service import RhythmAlignmentResult
from services.scoring_config import RhythmThresholds
from services.scoring import RhythmDiagnosis

logger = logging.getLogger(__name__)


class RhythmScorer:
    """
    节奏评分器

    专业标准：
    - 满分：偏差 <= excellent 拍长
    - 良好：偏差 <= good 拍长
    - 合格：偏差 <= pass 拍长
    - 底线：完全脱离节拍，上限60分
    """

    def __init__(self, thresholds: RhythmThresholds):
        """
        初始化节奏评分器

        Args:
            thresholds: 节奏阈值配置
        """
        self.thresholds = thresholds

    def calculate(
        self,
        rhythm_alignment: RhythmAlignmentResult
    ) -> Tuple[float, RhythmDiagnosis]:
        """
        计算节奏评分

        Args:
            rhythm_alignment: 节奏对齐分析结果

        Returns:
            (分数, 诊断信息)
        """
        diagnosis = RhythmDiagnosis()
        deviation = rhythm_alignment.avg_deviation_ratio

        # 使用配置计算基础分
        score, level = self.thresholds.get_score(deviation)
        diagnosis.level = level

        # 节奏不规则度惩罚
        if rhythm_alignment.irregularity > 0.3:
            penalty = min(15, rhythm_alignment.irregularity * 30)
            score -= penalty
            diagnosis.issues.append(f"节奏不规则度较高({rhythm_alignment.irregularity*100:.0f}%)")

        # 节拍密度异常
        bps = rhythm_alignment.beats_per_second
        if bps > 0 and (bps < 0.5 or bps > 5):
            diagnosis.issues.append(f"节拍密度异常({bps:.1f} beats/s)")

        score = max(0, min(100, score))

        diagnosis.score = score
        diagnosis.deviation_ratio = deviation

        if deviation > self.thresholds.pass_threshold:
            diagnosis.suggestions.append("建议配合节拍器练习，加强节奏感")

        return score, diagnosis
