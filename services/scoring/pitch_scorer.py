"""
音准评分器

负责音准维度的评分计算和诊断生成
"""
from typing import Tuple
import logging

from services.audio_features_service import PitchDeviationResult
from services.scoring_config import PitchThresholds
from services.scoring import PitchDiagnosis

logger = logging.getLogger(__name__)


class PitchScorer:
    """
    音准评分器

    专业标准：
    - 满分：MAE_c <= excellent 音分（人耳几乎不可辨）
    - 良好：MAE_c <= good 音分
    - 合格：MAE_c <= pass 音分
    - 底线：连续超过阈值个音符跑调超半音，扣20分
    """

    def __init__(self, thresholds: PitchThresholds):
        """
        初始化音准评分器

        Args:
            thresholds: 音准阈值配置
        """
        self.thresholds = thresholds

    def calculate(
        self,
        pitch_deviation: PitchDeviationResult
    ) -> Tuple[float, PitchDiagnosis]:
        """
        计算音准评分

        Args:
            pitch_deviation: 音高偏差分析结果

        Returns:
            (分数, 诊断信息)
        """
        diagnosis = PitchDiagnosis()
        mae = pitch_deviation.mae_cents

        # 使用配置计算基础分
        score, level = self.thresholds.get_score(mae)
        diagnosis.level = level

        # 检测率惩罚
        if pitch_deviation.detection_rate < 0.5:
            penalty = (0.5 - pitch_deviation.detection_rate) * 30
            score -= penalty
            diagnosis.issues.append(f"音高检测率低({pitch_deviation.detection_rate*100:.0f}%)")

        # 音高断层惩罚
        if pitch_deviation.pitch_breaks > 3:
            penalty = min(15, pitch_deviation.pitch_breaks * 2)
            score -= penalty
            diagnosis.issues.append(f"换声区存在{pitch_deviation.pitch_breaks}处音高断层")

        # 长音波动惩罚
        if pitch_deviation.pitch_wobble > 30:
            penalty = min(10, (pitch_deviation.pitch_wobble - 30) * 0.3)
            score -= penalty
            diagnosis.issues.append(f"长音波动较大({pitch_deviation.pitch_wobble:.0f}音分)")

        score = max(0, min(100, score))

        # 诊断信息
        diagnosis.score = score
        diagnosis.mae_cents = mae

        if mae > self.thresholds.pass_threshold:
            diagnosis.suggestions.append("建议加强音准训练，注意听标准音高")
        if pitch_deviation.pitch_breaks > 0:
            diagnosis.suggestions.append("换声区过渡需要更平滑，可练习音阶过渡")

        return score, diagnosis
