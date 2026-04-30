"""
后台任务工作模块

此文件保留为向后兼容的代理模块。
实际实现已重构到 core/workers/ 子模块中。
"""
from .workers import (
    WorkerSignals,
    AudioCache,
    get_audio_cache,
    EmotionAnalyzer,
    get_emotion_analyzer,
    AudioLoadTask,
    AssessmentTask,
    WorkerManager,
)

__all__ = [
    'WorkerSignals',
    'AudioCache',
    'get_audio_cache',
    'EmotionAnalyzer',
    'get_emotion_analyzer',
    'AudioLoadTask',
    'AssessmentTask',
    'WorkerManager',
]
