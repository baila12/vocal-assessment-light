"""
深度学习服务模块
提供人声质量检测、唱法识别、自参照DTW等深度学习功能
v5.12: 移除未使用的 CREPE、EnhancedDLAssessor、SpeechBrain MOS 代码
v7.12: 移除死代码 model_manager/ 子包、enhanced_dl_assessor (ScoreCalibrator)、桩文件
"""

from .voice_quality_detector import VoiceQualityDetector
from .singing_style_classifier import SingingStyleClassifier
from .self_referenced_dtw import SelfReferencedDTW

__all__ = [
    'VoiceQualityDetector',
    'SingingStyleClassifier',
    'SelfReferencedDTW',
]
