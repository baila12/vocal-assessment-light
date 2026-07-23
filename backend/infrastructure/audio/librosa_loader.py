"""
LibrosaAudioLoader — v7.1 Phase C

音频文件加载适配器。封装 librosa.load() 提供统一接口。

支持格式: WAV, MP3, FLAC, OGG, M4A, AAC
"""

from __future__ import annotations
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import librosa

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AudioData:
    """加载后的音频数据 (不可变)"""
    samples: np.ndarray  # float32, shape (n_samples,)
    sample_rate: int
    duration_s: float
    filepath: str
    is_mono: bool


class AudioLoadError(Exception):
    """音频加载失败"""
    pass


class LibrosaAudioLoader:
    """
    音频加载器 — DDD infrastructure 适配器。

    用法:
        loader = LibrosaAudioLoader(target_sr=22050)
        audio = loader.load("/path/to/song.wav")
    """

    SUPPORTED_EXTENSIONS = {'.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac'}

    def __init__(self, target_sr: int = 22050, mono: bool = True) -> None:
        self._target_sr = target_sr
        self._mono = mono

    def load(self, filepath: str | Path) -> AudioData:
        """加载音频文件"""
        filepath = Path(filepath)

        if not filepath.exists():
            raise AudioLoadError(f"File not found: {filepath}")

        ext = filepath.suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise AudioLoadError(
                f"Unsupported format: {ext}. Supported: {self.SUPPORTED_EXTENSIONS}"
            )

        try:
            y, sr = librosa.load(
                str(filepath),
                sr=self._target_sr,
                mono=self._mono,
            )
        except Exception as e:
            raise AudioLoadError(f"Failed to load {filepath.name}: {e}") from e

        if len(y) == 0:
            raise AudioLoadError(f"Audio file is empty: {filepath.name}")

        duration = len(y) / sr
        if duration < 0.1:
            logger.warning("Very short audio (<100ms): %s (%.2fs)", filepath.name, duration)

        return AudioData(
            samples=y.astype(np.float32),
            sample_rate=sr,
            duration_s=round(duration, 3),
            filepath=str(filepath),
            is_mono=self._mono or y.ndim == 1,
        )
