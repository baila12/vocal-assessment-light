"""音频处理适配器 — v7.1"""

from backend.infrastructure.audio.librosa_loader import LibrosaAudioLoader, AudioData, AudioLoadError
from backend.infrastructure.audio.pyin_extractor import PYINPitchExtractor, PitchResult, PitchExtractionError
from backend.infrastructure.audio.demucs_separator import DemucsSeparator, SeparationResult, SeparationError
from backend.infrastructure.audio.protocols import AudioLoader, PitchExtractor, VoiceSeparator

__all__ = [
    "LibrosaAudioLoader", "AudioData", "AudioLoadError",
    "PYINPitchExtractor", "PitchResult", "PitchExtractionError",
    "DemucsSeparator", "SeparationResult", "SeparationError",
    "AudioLoader", "PitchExtractor", "VoiceSeparator",
]
