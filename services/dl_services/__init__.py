"""
深度学习服务模块
提供人声质量检测、唱法识别、自参照DTW等深度学习功能
"""

from .voice_quality_detector import VoiceQualityDetector
from .singing_style_classifier import SingingStyleClassifier
from .self_referenced_dtw import SelfReferencedDTW
from .model_manager import DLModelManager

__all__ = [
    'VoiceQualityDetector',
    'SingingStyleClassifier',
    'SelfReferencedDTW',
    'DLModelManager'
]
