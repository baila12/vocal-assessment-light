"""
业务逻辑层

将路由层的业务逻辑抽离到独立模块
v5.12: 移除 Legacy 对比评分函数（calculate_comparison, generate_comparison_suggestions）
       所有对比分析统一通过 ComparisonService (DTW) 完成
"""
from .audio_analysis import analyze_and_score, analyze_emotion
from services.comparison import compare_with_dtw, ComparisonService

__all__ = [
    'analyze_and_score',
    'analyze_emotion',
    'compare_with_dtw',
    'ComparisonService',
]