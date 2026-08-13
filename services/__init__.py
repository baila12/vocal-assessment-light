"""
业务层 - 服务模块
负责核心业务逻辑，隔离接口层与数据层
"""

def __getattr__(name):
    import importlib
    _mapping = {
        "SeparationService": ".separation_service",
        "SeparationResult": ".separation_service",
        "ReportService": ".report_service",
        "ReportResult": ".report_service",
        "AudioService": ".audio_service",
        "AudioAnalysisResult": ".audio_service",
        # v7.16 P2-15 Phase 1: AdviceService 迁入 DDD application (AdviceGenerator)
        "VisualizationService": ".visualization_service",
        "VisualizationResult": ".visualization_service",
        "TimbreService": ".timbre_service",
        "TimbreResult": ".timbre_service",
        "PhraseService": ".phrase_service",
        "PhraseResult": ".phrase_service",
        "PhraseScore": ".phrase_service",
        "VoiceQualityService": ".voice_quality_service",
        "VoiceQualityResult": ".voice_quality_service",
    }
    if name in _mapping:
        mod = importlib.import_module(_mapping[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "AudioService", "AudioAnalysisResult",
    "VisualizationService", "VisualizationResult",
    "SeparationService", "SeparationResult",
    "TimbreService", "TimbreResult",
    "PhraseService", "PhraseResult", "PhraseScore",
    "ReportService", "ReportResult",
    "VoiceQualityService", "VoiceQualityResult",
]