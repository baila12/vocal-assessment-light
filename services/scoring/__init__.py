"""
评分结果数据传输对象 (DTOs) 和评分器模块

定义评分和诊断结果的数据结构，以及各维度评分器
"""
from .types import (
    PitchDiagnosis,
    RhythmDiagnosis,
    BreathDiagnosis,
    TechniqueDiagnosis,
    ArtistryDiagnosis,
    ScoreResultV4,
    ScoreResult,
)

# 延迟导入评分器 — 避免循环依赖
def __getattr__(name):
    import importlib
    _mapping = {
        "PitchScorer": ".pitch_scorer",
        "RhythmScorer": ".rhythm_scorer",
        "BreathScorer": ".breath_scorer",
        "TechniqueScorer": ".technique_scorer",
        "ArtistryScorer": ".artistry_scorer",
        "CriticalRulesHandler": ".critical_rules",
    }
    if name in _mapping:
        mod = importlib.import_module(_mapping[name], __package__)
        return getattr(mod, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    # DTOs
    'PitchDiagnosis',
    'RhythmDiagnosis',
    'BreathDiagnosis',
    'TechniqueDiagnosis',
    'ArtistryDiagnosis',
    'ScoreResultV4',
    'ScoreResult',
    # Scorers
    'PitchScorer',
    'RhythmScorer',
    'BreathScorer',
    'TechniqueScorer',
    'ArtistryScorer',
    'CriticalRulesHandler',
]