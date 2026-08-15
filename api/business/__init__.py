"""
业务逻辑层

将路由层的业务逻辑抽离到独立模块
v5.12: 移除 Legacy 对比评分函数（calculate_comparison, generate_comparison_suggestions）
v7.19 E1: 移除 compare_with_dtw 导出 — 对比评分统一走 DDD CompareAudioUseCase
       (ComparisonService 仅为偏差提供者, 由 DDD 应用层编排)
"""
from .audio_analysis import analyze_and_score
from services.comparison import ComparisonService

__all__ = [
    'analyze_and_score',
    'ComparisonService',
]