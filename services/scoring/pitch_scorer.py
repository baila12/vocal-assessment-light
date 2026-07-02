"""
音准评分器 v5.14

负责音准维度的评分计算和诊断生成。
v5.14: 多指标字段 (RPA/RCA/gross_error/octave_error/smoothness) 已计算但暂不驱动评分。
       无参考音高时，MAE 线性映射仍是经过验证的最可靠方法。
       多指标字段保留供校准数据集 (Phase 3) 后使用。
"""
from typing import Tuple
import logging

from services.audio_features_service import PitchDeviationResult
from services.scoring_config import PitchThresholds, EmpiricalThresholds
from services.scoring.types import PitchDiagnosis

logger = logging.getLogger(__name__)


class PitchScorer:
    """音准评分器 v5.14"""

    def __init__(self, thresholds: PitchThresholds, empirical: EmpiricalThresholds = None):
        self.thresholds = thresholds
        self.empirical = empirical or EmpiricalThresholds()

    def calculate(
        self,
        pitch_deviation: PitchDeviationResult
    ) -> Tuple[float, PitchDiagnosis]:
        """
        计算音准评分

        v5.14: 多指标字段已计算 (RPA/RCA/gross_error/octave_error/smoothness)
        但因无参考音高，加权公式暂不启用。保留字段供校准后用。
        """
        diagnosis = PitchDiagnosis()
        mae = pitch_deviation.mae_cents

        # 使用 MAE 线性映射 (经过验证)
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
        wobble_threshold = self.empirical.pitch_wobble_threshold
        if pitch_deviation.pitch_wobble > wobble_threshold:
            penalty = min(10, (pitch_deviation.pitch_wobble - wobble_threshold) * 0.3)
            score -= penalty
            diagnosis.issues.append(f"长音波动较大({pitch_deviation.pitch_wobble:.0f}音分)")

        # v5.14: 多指标诊断 (仅诊断，不驱动评分)
        if pitch_deviation.rpa > 0:
            if pitch_deviation.gross_error_rate > 0.05:
                diagnosis.issues.append(f"严重跑调比例({pitch_deviation.gross_error_rate*100:.0f}%)")
            if pitch_deviation.relative_smoothness > 2.0:
                diagnosis.issues.append(f"音高一致性偏低(smoothness={pitch_deviation.relative_smoothness:.1f})")

        score = max(0, min(100, score))

        diagnosis.score = score
        diagnosis.mae_cents = mae

        if score < 60:
            diagnosis.suggestions.append("建议加强音准训练，注意听标准音高")
        if pitch_deviation.pitch_breaks > 0:
            diagnosis.suggestions.append("换声区过渡需要更平滑，可练习音阶过渡")

        return score, diagnosis
