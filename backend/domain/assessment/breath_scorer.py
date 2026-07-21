"""
气息评分器 v7.0 — 移植 v6.3 四子维度连续线性映射

四大细分维度: 长音支撑(40%)、动态控制(25%)、气口设计(20%)、气声技巧(15%)
"""

from __future__ import annotations
from dataclasses import dataclass

from backend.domain.assessment.value_objects import BreathScore


@dataclass
class BreathFeatures:
    """气息特征输入"""
    professional_breath_score: float = 0.0
    long_note_support: float = 0.0
    dynamic_control: float = 0.0
    breath_design: float = 0.0
    breath_technique: float = 0.0
    rms_fluctuation: float = 0.0
    is_artistic_fluctuation: bool = False
    controlled_breathiness: float = 0.0
    uncontrolled_leak: float = 0.0
    breath_breaks: int = 0
    long_note_count: int = 0
    soft_segment_count: int = 0
    soft_singing_quality: float = 0.0
    clean_breath_count: int = 0
    dynamic_range: float = 0.0
    is_clean_vocal: bool = False


class BreathScorer:
    """气息评分器 — 纯计算, 零副作用"""

    def calculate(self, features: BreathFeatures) -> BreathScore:
        # 1. 主分: professional score 优先, 否则 fallback 到 fluctuation
        if features.professional_breath_score > 0:
            score = features.professional_breath_score
        else:
            score = self._score_from_fluctuation(features.rms_fluctuation)

        # 2. 长音加分
        if features.long_note_support > 80:
            score += 5.0
        elif features.long_note_support > 60:
            pass  # 良好无加分

        # 3. 弱唱加分
        if features.soft_singing_quality > 70:
            score += 5.0
        elif features.soft_singing_quality > 50:
            pass

        # 4. 气息断层惩罚
        if features.breath_breaks > 3:
            penalty = min(15.0, (features.breath_breaks - 3) * 3.0)
            score -= penalty

        score = max(0.0, min(100.0, score))

        diagnosis: list[str] = []
        if features.is_artistic_fluctuation:
            diagnosis.append("检测到艺术化的强弱起伏处理")
        if features.uncontrolled_leak > 30:
            diagnosis.append("存在无效漏气")
        if features.breath_breaks > 3:
            diagnosis.append(f"存在{features.breath_breaks}处气息断层")

        return BreathScore(
            raw_score=round(score, 1),
            long_note_support=features.long_note_support,
            dynamic_control=features.dynamic_control,
            breath_design=features.breath_design,
            breath_technique=features.breath_technique,
            is_clean_vocal=features.is_clean_vocal,
            dynamic_range_db=features.dynamic_range,
            diagnosis=tuple(diagnosis),
        )

    @staticmethod
    def _score_from_fluctuation(fluctuation: float) -> float:
        """从 RMS 波动率计算基础分 (fallback)"""
        if fluctuation <= 0.20:
            return 100.0
        elif fluctuation <= 0.35:
            return 100.0 - (fluctuation - 0.20) * 250  # 100→62.5
        elif fluctuation <= 0.50:
            return 62.5 - (fluctuation - 0.35) * 250   # 62.5→25
        else:
            return max(10.0, 25.0 - (fluctuation - 0.50) * 100)
