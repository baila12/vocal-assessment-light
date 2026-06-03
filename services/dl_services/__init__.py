"""
深度学习服务模块
提供人声质量检测、唱法识别、自参照DTW等深度学习功能
v1.1 新增：增强的DL评估器、评分校准器
v1.2 新增：模型诊断工具
v5.12: 移除未使用的 CREPE、EnhancedDLAssessor、SpeechBrain MOS 代码
"""

from .voice_quality_detector import VoiceQualityDetector
from .singing_style_classifier import SingingStyleClassifier
from .self_referenced_dtw import SelfReferencedDTW
from .model_manager import DLModelManager, ModelDiagnostic

# v1.1 评分校准器（供测试使用，生产路径未调用）
from .enhanced_dl_assessor import ScoreCalibrator

__all__ = [
    'VoiceQualityDetector',
    'SingingStyleClassifier',
    'SelfReferencedDTW',
    'DLModelManager',
    'ModelDiagnostic',
    # v1.1
    'ScoreCalibrator',
]
