"""
节奏评分器 v7.0 — 移植 v6.3 onset CV + irregularity

使用onset间隔变异系数(CV)评估节奏规律性，不依赖beat_track。
支持无伴奏独唱、弹性速度(Rubato)、非西方节奏体系。
"""

from __future__ import annotations
from dataclasses import dataclass

from backend.domain.assessment.value_objects import RhythmScore


@dataclass(frozen=True)
class RhythmFeatures:
    """节奏特征输入 (不可变)"""
    avg_deviation_ratio: float = 0.0
    irregularity: float = 0.0       # onset间隔 CV
    onset_density: float = 2.0      # events/second
    onset_count: int = 100
    off_beat_segments: int = 0
    is_clean_vocal: bool = False


class RhythmScorer:
    """节奏评分器 — 纯计算, 零副作用"""

    def calculate(self, features: RhythmFeatures) -> RhythmScore:
        deviation = features.avg_deviation_ratio

        # 1. 基础分 from deviation ratio (分段线性)
        if deviation <= 0.10:
            base_score = 100.0
        elif deviation <= 0.20:
            base_score = 100.0 - (deviation - 0.10) * 200  # 100→80
        elif deviation <= 0.30:
            base_score = 80.0 - (deviation - 0.20) * 300   # 80→50
        else:
            base_score = max(20.0, 50.0 - (deviation - 0.30) * 200)

        score = base_score

        # 2. Irregularity 惩罚 (CV-based, 分级)
        irr = features.irregularity
        if irr > 0.5:
            if irr > 1.2:
                penalty = min(25.0, 10.0 + (irr - 1.2) * 15.0)
            elif irr > 0.8:
                penalty = min(15.0, (irr - 0.5) * 25.0)
            elif irr > 0.5:
                penalty = (irr - 0.5) * 15.0
            else:
                penalty = 0.0
            score -= penalty
            irregularity_penalty = penalty
        else:
            irregularity_penalty = 0.0

        score = max(0.0, min(100.0, score))

        diagnosis: list[str] = []
        if irr > 1.2:
            diagnosis.append(f"节奏极不规则CV={irr*100:.0f}%")
        elif irr > 0.5:
            diagnosis.append(f"节奏略有波动CV={irr*100:.0f}%")

        return RhythmScore(
            raw_score=round(score, 1),
            onset_cv=features.avg_deviation_ratio,
            median_ioi_deviation=deviation,
            irregularity_penalty=round(irregularity_penalty, 2),
            is_clean_vocal=features.is_clean_vocal,
            diagnosis=tuple(diagnosis),
        )
