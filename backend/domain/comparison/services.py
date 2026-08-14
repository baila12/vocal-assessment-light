"""
Comparison 领域服务 — v7.3 Phase 2

DDD 对比分析领域服务:
  - ComparisonScoringService: 偏差→评分 (移植 scoring_engine.py 算法)
"""

from __future__ import annotations
from typing import List

from backend.domain.comparison.entities import DeviationData, AlignmentData
from backend.domain.comparison.value_objects import (
    ComparisonScores, DimensionComparisonScore,
)


class ComparisonScoringService:
    """对比评分领域服务 — 纯计算, 零副作用

    移植自 services/comparison/scoring_engine.py (四维加权评分引擎)。
    支持 4 种风格自适应权重。
    """

    # 风格权重
    STYLE_WEIGHTS = {
        "pop": {"pitch": 0.40, "rhythm": 0.30, "volume": 0.15, "breath": 0.15},
        "classical": {"pitch": 0.50, "rhythm": 0.20, "volume": 0.20, "breath": 0.10},
        "folk": {"pitch": 0.35, "rhythm": 0.25, "volume": 0.20, "breath": 0.20},
        "rap": {"pitch": 0.20, "rhythm": 0.50, "volume": 0.20, "breath": 0.10},
    }

    def score(
        self,
        deviation: DeviationData,
        confidence: float = 1.0,
        style: str = "pop",
    ) -> ComparisonScores:
        """从偏差数据计算四维度对比评分"""
        weights = self.STYLE_WEIGHTS.get(style, self.STYLE_WEIGHTS["pop"])

        pitch = self._score_pitch(deviation)
        rhythm = self._score_rhythm(deviation)
        volume = self._score_volume(deviation)
        breath = self._score_breath(deviation)

        return ComparisonScores(
            pitch=pitch,
            rhythm=rhythm,
            volume=volume,
            breath=breath,
            _confidence=confidence,
            _weights=(weights["pitch"], weights["rhythm"], weights["volume"], weights["breath"]),
        )

    @staticmethod
    def _score_pitch(dev: DeviationData) -> DimensionComparisonScore:
        """音准评分 — 分段线性曲线"""
        avg_cents = abs(dev.avg_pitch_cents)
        max_cents = dev.max_pitch_cents

        if avg_cents <= 0:
            s = 100.0
        elif avg_cents <= 50:
            s = 100.0 - (avg_cents / 50.0) * 25.0
        elif avg_cents <= 100:
            s = 75.0 - ((avg_cents - 50.0) / 50.0) * 50.0
        else:
            s = max(10.0, 25.0 - ((avg_cents - 100.0) / 50.0) * 15.0)

        return DimensionComparisonScore(
            score=round(s, 1),
            avg_deviation=round(avg_cents, 1),
            max_deviation=round(max_cents, 1),
            problem_count=dev.problem_frame_count,
            details={
                # v7.18 P1 (F2): 八度错误率 (独立信号, 折叠后评分已公平)
                "octave_error_rate": round(dev.octave_error_rate, 4),
            },
        )

    @staticmethod
    def _score_rhythm(dev: DeviationData) -> DimensionComparisonScore:
        """节奏评分"""
        avg_ms = abs(dev.avg_rhythm_ms)
        if avg_ms <= 50:
            s = 100.0
        else:
            s = max(10.0, 100.0 - (avg_ms - 50.0) / 5.0)

        return DimensionComparisonScore(
            score=round(s, 1),
            avg_deviation=round(avg_ms, 1),
            max_deviation=0.0,
            problem_count=0,
            details={
                # v7.18 P1 (F1): 整体速度比 (用户相对参考, 1.0=同速)
                "tempo_ratio": round(dev.tempo_ratio, 4),
            },
        )

    @staticmethod
    def _score_volume(dev: DeviationData) -> DimensionComparisonScore:
        """音量评分 — v7.18 P1 (F3): 动态匹配偏差 (z-score, 0-~2), 录音增益已归一"""
        avg_dev = abs(dev.avg_volume_percent)
        s = max(0.0, (1.0 - avg_dev) * 100.0)

        return DimensionComparisonScore(
            score=round(s, 1),
            avg_deviation=round(avg_dev, 3),
            max_deviation=0.0,
            problem_count=0,
            details={"avg_dynamic_deviation": round(avg_dev, 3)},
        )

    @staticmethod
    def _score_breath(dev: DeviationData) -> DimensionComparisonScore:
        """气息评分"""
        stability = dev.avg_breath_stability
        s = max(0.0, min(100.0, stability * 100.0))

        return DimensionComparisonScore(
            score=round(s, 1),
            avg_deviation=round(1.0 - stability, 2),
            max_deviation=0.0,
            problem_count=0,
            details=(),
        )

    def generate_suggestions(self, deviation: DeviationData) -> List[str]:
        """根据偏差数据生成改进建议"""
        suggestions: list[str] = []

        avg_cents = abs(deviation.avg_pitch_cents)
        avg_ms = abs(deviation.avg_rhythm_ms)
        stability = deviation.avg_breath_stability

        if avg_cents > 50:
            suggestions.append(
                f"音准偏差较大（平均{avg_cents:.0f}音分），建议练习音阶，注意音高准确性"
            )
        elif avg_cents > 20:
            suggestions.append(
                f"音准整体良好，部分段落略有偏差，建议多听标准音频找准音高"
            )

        if avg_ms > 150:
            suggestions.append(
                f"节奏偏差明显（平均{avg_ms:.0f}ms），建议跟着节拍器练习"
            )
        elif avg_ms > 50:
            suggestions.append("节奏基本正确，注意不要抢拍或拖拍")

        if stability < 0.6:
            suggestions.append("气息稳定性不足，建议练习腹式呼吸，增强气息控制能力")

        if not suggestions:
            suggestions.append("表现优秀！与标准音频高度匹配，继续保持练习")

        return suggestions
