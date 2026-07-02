"""
音频特征数据传输对象 (DTOs) 和分析器模块

定义音频特征提取结果的统一数据结构，以及各维度分析器
"""
from .types import (
    PitchDeviationResult,
    RhythmAlignmentResult,
    BreathStabilityResult,
    VocalTechniqueResult,
    AudioFeaturesResult,
    AcousticResult,
)

# 导出分析器
from .pitch import PitchAnalyzer
from .rhythm import RhythmAnalyzer
from .breath import BreathAnalyzer
from .technique import TechniqueAnalyzer
from .acoustic import AcousticAnalyzer

__all__ = [
    # DTOs
    'PitchDeviationResult',
    'RhythmAlignmentResult',
    'BreathStabilityResult',
    'VocalTechniqueResult',
    'AudioFeaturesResult',
    'AcousticResult',
    # Analyzers
    'PitchAnalyzer',
    'RhythmAnalyzer',
    'BreathAnalyzer',
    'TechniqueAnalyzer',
    'AcousticAnalyzer',
]