"""
特征提取器 Protocol 接口 — v7.1 Batch 1

领域层定义抽象接口，基础设施层提供具体实现。
遵循依赖倒置原则 (DIP): Domain 定义契约, Infrastructure 实现。

设计原则:
  - 每个 Protocol 单一职责: 输入 (y, sr, ...) → 输出 XXXFeatures
  - 零副作用: 纯计算, 无 I/O
  - 独立可测: 可用合成音频验证
  - 启发式标记: Muscle/Timbre 在输出中标记 is_heuristic=True
"""
from __future__ import annotations
from typing import Protocol, runtime_checkable
import numpy as np


# Forward references — imported at call time to avoid circular imports
# AcousticFeatures is defined in feature_types.py (same package)


@runtime_checkable
class AcousticFeatureExtractor(Protocol):
    """
    声学基础特征提取器 Protocol — Level 0

    输入原始音频 → 输出 AcousticFeatures
    整合: HNR, CPP, spectral_tilt, voicing, mixed-audio detection
    """

    def extract(
        self,
        y: np.ndarray,
        sr: int,
        enable_multiscale_hnr: bool = True,
        enable_praat_cpp: bool = True,
        enable_voicing_detection: bool = True,
        enable_reverb_compensation: bool = False,
    ) -> "AcousticFeatures":
        ...


@runtime_checkable
class PitchFeatureExtractor(Protocol):
    """
    音准特征提取器 Protocol — Level 1

    输入 F0 + voiced flags → 输出 PitchFeatures
    (仅定义签名, Batch 2 实现)
    """

    def extract(
        self,
        y: np.ndarray,
        sr: int,
        f0: np.ndarray,
        voiced_flags: np.ndarray,
    ) -> "PitchFeatures":
        ...


@runtime_checkable
class RhythmFeatureExtractor(Protocol):
    """
    节奏特征提取器 Protocol — Level 1

    输入音频 + onset → 输出 RhythmFeatures
    (仅定义签名, Batch 3 实现)
    """

    def extract(
        self,
        y: np.ndarray,
        sr: int,
        onset_env: np.ndarray | None = None,
        is_clean_vocal: bool = False,
    ) -> "RhythmFeatures":
        ...
