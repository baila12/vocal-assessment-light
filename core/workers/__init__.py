"""
后台任务工作模块

导出所有工作类和管理器
"""
from .signals import WorkerSignals
from .cache import AudioCache, get_audio_cache
from .emotion_analyzer import EmotionAnalyzer, get_emotion_analyzer
from .audio_loader import AudioLoadTask
from .assessment_task import AssessmentTask
from .manager import WorkerManager

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
