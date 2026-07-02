"""
深度学习服务 (DL Services)

注意: AI模型加载较重，在使用时才初始化。
此模块在 v2.0 重构中已废弃，保留空桩防止导入错误。
"""
import logging

logger = logging.getLogger(__name__)

class VoiceQualityDetector:
    """人声质量检测器 (桩) — 功能已合并到 VoiceQualityService"""
    def __init__(self):
        self.available = False

    def detect(self, audio_data, sample_rate):
        return {"available": False, "message": "DL service not available"}


class SingingStyleClassifier:
    """唱法分类器 (桩) — 功能已合并到 StyleAnalyzer"""
    def __init__(self):
        self.available = False

    def classify(self, audio_data, sample_rate):
        return {"style": "unknown", "confidence": 0.0}


class SelfReferencedDTW:
    """自参考DTW对齐 (桩) — 功能已合并到 PhraseService"""
    def __init__(self):
        pass

    def align(self, audio_data, sample_rate):
        return {"aligned": False}