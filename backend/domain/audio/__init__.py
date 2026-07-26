"""
音频处理上下文 — v7.2

DDD 特征提取层:
  - feature_types: 声学特征数据类型 (AcousticFeatures)
  - feature_protocols: 提取器 Protocol 接口 (依赖倒置)
  - acoustic_feature_extractor: LibrosaAcousticExtractor (Level 0)
  - pitch_extractor: LibrosaPitchExtractor (Level 1)
  - rhythm_extractor: LibrosaRhythmExtractor (Level 1)
  - audiofeat_extractor: AudiofeatExtractor (v7.2 — 20+ 增强特征)
"""
from backend.domain.audio.feature_types import AcousticFeatures
from backend.domain.audio.feature_protocols import (
    AcousticFeatureExtractor,
    PitchFeatureExtractor,
    RhythmFeatureExtractor,
)
from backend.domain.audio.acoustic_feature_extractor import LibrosaAcousticExtractor
from backend.domain.audio.pitch_extractor import LibrosaPitchExtractor
from backend.domain.audio.rhythm_extractor import LibrosaRhythmExtractor
from backend.domain.audio.audiofeat_extractor import (
    AudiofeatExtractor,
    AudiofeatFeatures,
)

__all__ = [
    # Types
    "AcousticFeatures",
    "AudiofeatFeatures",
    # Protocols
    "AcousticFeatureExtractor",
    "PitchFeatureExtractor",
    "RhythmFeatureExtractor",
    # Implementations
    "LibrosaAcousticExtractor",
    "LibrosaPitchExtractor",
    "LibrosaRhythmExtractor",
    # Audiofeat (v7.2)
    "AudiofeatExtractor",
]
