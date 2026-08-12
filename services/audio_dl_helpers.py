"""
AudioService DL 辅助方法 v5.18

从 audio_service.py 提取的深度学习延迟初始化与执行方法，
保持 AudioService 文件大小在 800 行以内。
"""
import logging

logger = logging.getLogger(__name__)


class AudioDLHelpers:
    """
    深度学习分析辅助方法集。

    从 AudioService 提取，包含:
    - 人声质量检测 (VoiceQualityDetector)
    - 唱法识别 (SingingStyleClassifier)
    - 自参照 DTW (SelfReferencedDTW)
    - 音乐风格分析 (StyleAnalyzer)
    """

    def __init__(self):
        self._voice_quality_detector = None
        self._style_classifier = None
        self._self_ref_dtw = None
        self._style_analyzer = None

    def _get_voice_quality_detector(self):
        """延迟初始化人声质量检测器"""
        if self._voice_quality_detector is None:
            from services.dl_services import VoiceQualityDetector
            self._voice_quality_detector = VoiceQualityDetector()
        return self._voice_quality_detector

    def _get_style_classifier(self):
        """延迟初始化唱法分类器"""
        if self._style_classifier is None:
            from services.dl_services import SingingStyleClassifier
            self._style_classifier = SingingStyleClassifier()
        return self._style_classifier

    def _get_self_ref_dtw(self):
        """延迟初始化自参照DTW"""
        if self._self_ref_dtw is None:
            from services.dl_services import SelfReferencedDTW
            self._self_ref_dtw = SelfReferencedDTW()
        return self._self_ref_dtw

    def _get_style_analyzer(self):
        """延迟初始化风格分析器 v5.1"""
        if self._style_analyzer is None:
            from services.style_aware_scorer import StyleAnalyzer
            self._style_analyzer = StyleAnalyzer(use_dl=True)
        return self._style_analyzer

    def run_voice_quality_detection(self, filepath: str):
        """运行人声质量检测"""
        try:
            detector = self._get_voice_quality_detector()
            return detector.detect(filepath)
        except Exception:
            # v7.15 M5: 保留根因 — 完整 traceback 入日志, 生产可诊断 DL 失败堆栈
            logger.warning("Voice quality detection failed", exc_info=True)
            return None

    def run_style_classification(self, filepath: str):
        """运行唱法识别"""
        try:
            classifier = self._get_style_classifier()
            return classifier.classify(filepath)
        except Exception:
            # v7.15 M5: 保留根因
            logger.warning("Style classification failed", exc_info=True)
            return None

    def run_self_referenced_dtw(self, filepath: str):
        """运行自参照DTW音准评估"""
        try:
            dtw = self._get_self_ref_dtw()
            return dtw.analyze(filepath)
        except Exception:
            # v7.15 M5: 保留根因
            logger.warning("Self-referenced DTW failed", exc_info=True)
            return None

    def run_music_style_analysis(self, filepath: str):
        """运行音乐风格分析 v5.1"""
        try:
            analyzer = self._get_style_analyzer()
            style, style_features = analyzer.analyze(filepath)
            profile = analyzer.get_style_profile(style)
            return style, profile, style_features
        except Exception:
            # v7.15 M5: 保留根因
            logger.warning("Music style analysis failed", exc_info=True)
            return None
