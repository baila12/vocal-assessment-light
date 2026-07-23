"""
音频处理 Protocol 接口 — v7.1 Phase C

定义音频加载器, 基频提取器, 人声分离器的协议接口。
DDD 领域层依赖这些抽象接口, 基础设施层提供具体实现。
"""

from __future__ import annotations
from typing import Protocol, runtime_checkable
import numpy as np


@runtime_checkable
class AudioLoader(Protocol):
    """音频加载器 Protocol"""

    def load(self, filepath: str) -> 'AudioData':
        ...


@runtime_checkable
class PitchExtractor(Protocol):
    """基频提取器 Protocol"""

    def extract(self, y: np.ndarray, sr: int) -> 'PitchResult':
        ...


@runtime_checkable
class VoiceSeparator(Protocol):
    """人声分离器 Protocol"""

    def separate(self, filepath: str) -> 'SeparationResult':
        ...
