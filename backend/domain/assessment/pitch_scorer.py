"""
音准评分器 v7.0 — 移植 v6.2 多指标体系

六指标加权融合:
  - MAE 指数衰减: 40% (最鲁棒的聚合指标)
  - RPA (Raw Pitch Accuracy): 25%
  - RCA (Raw Chroma Accuracy): 10%
  - Gross error 惩罚: 15%
  - Smoothness: 5%
  - Octave error 惩罚: 5%

文献依据: Wager et al. (2022), Cao et al. (2008), de Cheveigne & Kawahara (2002)
"""

from __future__ import annotations
from dataclasses import dataclass
import numpy as np

from backend.domain.assessment.value_objects import PitchScore

_MAE_TAU = 40.0  # 指数衰减时间常数


@dataclass
class PitchFeatures:
    """音准特征输入 (纯数据, 零行为)"""
    mae_cents: float = 0.0
    rpa: float = 0.0       # 0-1
    rca: float = 0.0       # 0-1
    gross_error_rate: float = 0.0
    octave_error_rate: float = 0.0
    relative_smoothness: float = 1.0
    detection_rate: float = 1.0
    pitch_breaks: int = 0
    valid_frame_count: int = 100
    pitch_wobble: float = 0.0


class PitchScorer:
    """音准评分器 — 纯计算, 零副作用"""

    def calculate(self, features: PitchFeatures) -> PitchScore:
        mae = features.mae_cents

        # 1. MAE 指数衰减 (40%)
        mae_score = 100.0 * np.exp(-mae / _MAE_TAU)

        # 2. RPA (25%)
        rpa_score = max(0.0, features.rpa) * 100.0

        # 3. RCA (10%)
        rca_score = max(0.0, features.rca) * 100.0

        # 4. Gross error 惩罚 (15%)
        gross_rate = features.gross_error_rate
        if gross_rate > 0.05:
            gross_penalty = min(100, (gross_rate - 0.05) * 200)
            gross_score = 100.0 - gross_penalty
        else:
            gross_score = 100.0

        # 5. Smoothness (5%) — YIN f0 帧间噪声大, 降低权重
        smoothness = features.relative_smoothness
        if smoothness > 0:
            smoothness_score = max(0, 100.0 - (smoothness - 1.0) * 50.0)
        else:
            smoothness_score = 50.0

        # 6. Octave error 惩罚 (5%)
        octave_score = max(0, 100.0 - features.octave_error_rate * 200.0)

        # 加权合成
        score = (
            mae_score * 0.40
            + rpa_score * 0.25
            + rca_score * 0.10
            + gross_score * 0.15
            + smoothness_score * 0.05
            + octave_score * 0.05
        )

        # 检测率惩罚
        diagnosis: list[str] = []
        if features.detection_rate < 0.5:
            penalty = (0.5 - features.detection_rate) * 30
            score -= penalty
            diagnosis.append(
                f"音高检测率低({features.detection_rate*100:.0f}%)"
            )

        # Pitch breaks 惩罚 (YIN 校准: ÷3.5)
        _YIN_INFLATION = 3.5
        if features.valid_frame_count > 0 and features.pitch_breaks > 0:
            est_pairs = features.valid_frame_count * max(features.detection_rate, 0.5)
            break_rate = features.pitch_breaks / max(est_pairs, 1)
            corrected_rate = break_rate / _YIN_INFLATION
            if corrected_rate > 0.05:
                penalty = min(15, (corrected_rate - 0.05) * 200)
                score -= penalty
                diagnosis.append(
                    f"换声区存在{features.pitch_breaks}处音高断层"
                )

        # Pitch wobble 惩罚
        wobble_threshold = 10.0
        if features.pitch_wobble > wobble_threshold:
            penalty = min(10, (features.pitch_wobble - wobble_threshold) * 0.3)
            score -= penalty
            diagnosis.append(
                f"长音波动较大({features.pitch_wobble:.0f}音分)"
            )

        score = max(0.0, min(100.0, score))

        return PitchScore(
            raw_score=round(score, 1),
            mae_cents=mae,
            rpa=features.rpa,
            rca=features.rca,
            gross_error_rate=features.gross_error_rate,
            octave_error_rate=features.octave_error_rate,
            smoothness_cv=features.relative_smoothness,
            detection_rate=features.detection_rate,
            pitch_breaks=features.pitch_breaks,
            diagnosis=tuple(diagnosis),
        )
