"""
对比分析模块 - 基于DTW的音频对比分析

实现三级DTW对齐：
1. 全局粗对齐（能量包络）
2. 句子级对齐（音高+能量+过零率）
3. 音符级精细对齐（逐音符DTW）

核心目标：
- 相同音频得分 ≥ 95分
- 支持1-10分钟音频
- API响应时间 < 3秒（3分钟音频）
"""

from .dtw_aligner import DTWAligner, MultiFeatureSequence, AlignmentResult
from .benchmark_service import BenchmarkService, BenchmarkFeatures
from .deviation_calculator import DeviationCalculator, DeviationResult, FrameDeviation
from .scoring_engine import ComparisonScoringEngine, ComparisonScoreResult, DimensionScore
from .comparison_service import ComparisonService, compare_with_dtw

__all__ = [
    'DTWAligner',
    'MultiFeatureSequence',
    'AlignmentResult',
    'BenchmarkService',
    'BenchmarkFeatures',
    'DeviationCalculator',
    'DeviationResult',
    'FrameDeviation',
    'ComparisonScoringEngine',
    'ComparisonScoreResult',
    'DimensionScore',
    'ComparisonService',
    'compare_with_dtw',
]
