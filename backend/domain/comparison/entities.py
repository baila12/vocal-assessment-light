"""
Comparison 实体 — v7.3 Phase 1

DDD 对比分析实体:
  - AlignmentData: DTW 对齐结果
  - DeviationData: 逐帧偏差聚合
  - ComparisonResult: 聚合根
"""

from __future__ import annotations
from dataclasses import dataclass

from backend.domain.comparison.value_objects import ComparisonScores


@dataclass(frozen=True)
class AlignmentData:
    """DTW 对齐结果 — 不可变"""
    confidence: float = 1.0            # 对齐置信度 (0-1)
    global_offset: float = 0.0        # 全局时间偏移 (秒)
    method: str = "three_level_dtw"   # 对齐方法
    compute_time_ms: float = 0.0      # 计算耗时


@dataclass(frozen=True)
class DeviationData:
    """逐帧偏差聚合 — 不可变"""
    avg_pitch_cents: float = 0.0
    max_pitch_cents: float = 0.0
    avg_rhythm_ms: float = 0.0
    avg_volume_percent: float = 0.0
    avg_breath_stability: float = 1.0
    problem_frame_count: int = 0
    # v7.18 P1 (F2/F1): 八度错误率 + 整体速度比 — 独立信号 (评分已含折叠/残差)
    octave_error_rate: float = 0.0
    tempo_ratio: float = 1.0


@dataclass(frozen=True)
class ComparisonResult:
    """对比分析聚合根 — 不可变

    包含完整的 DTW 对比分析结果: 对齐 + 偏差 + 评分
    """
    alignment: AlignmentData = AlignmentData()
    deviation: DeviationData = DeviationData()
    scoring: ComparisonScores = ComparisonScores()
    method: str = "three_level_dtw"
    compute_time_ms: float = 0.0

    @property
    def overall_score(self) -> float:
        return self.scoring.weighted_total()

    @property
    def level(self) -> str:
        from backend.shared.domain_types import ScoreLevel
        return ScoreLevel.from_score(self.overall_score).label
