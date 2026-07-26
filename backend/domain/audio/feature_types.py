"""
声学特征数据类型 — v7.1 Batch 1: Acoustic Foundation

DDD 特征提取器层级:
  Level 0: AcousticFeatures — 基础声学测量 (HNR, CPP, spectral_tilt, voicing)
  Level 1: PitchFeatures, RhythmFeatures — 独立维度 (仅依赖原始音频/F0)
  Level 2: BreathFeatures, TechniqueFeatures, TimbreFeatures — 依赖 AcousticFeatures
  Level 3: MuscleFeatures, ArtistryFeatures — 依赖 Level 1+2 的输出

所有类型使用 frozen=True，确保不可变性。
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import numpy as np


@dataclass(frozen=True)
class AcousticFeatures:
    """声学基础特征 — Level 0, 零上游依赖, 被多个下游提取器消费。

    从原始音频中提取的频率域和倒谱域基础测量:
      - HNR (谐波噪声比): 反映声带闭合程度, 通过 HPSS 能量比计算
      - CPP (倒谱峰值显著性): 反映声带闭合质量, 通过倒谱分析计算
      - Spectral Tilt (频谱倾斜): 区分气声 vs 压嗓 [Sundberg 1987]
      - Voicing: 有声/无声检测 + 置信度
      - Mixed Audio: 混合音频检测 (人声+伴奏)

    Attributes:
        hnr: 谐波噪声比 (dB), 正常范围 5-35 dB, 默认 0
        cpp: 倒谱峰值显著性, 正常范围 0-6, 默认 0
        spectral_tilt: LTAS 斜率 (dB/oct), 正常范围 -15 到 +5, 负值=气声
        voicing_ratio: 有声帧比例 (0-1), 默认 0
        detection_confidence: PYIN 检测置信度均值 (0-1), 默认 0
        is_mixed_audio: 是否检测到混合音频 (人声+伴奏), 默认 False
        mixed_audio_confidence: 混合音频检测置信度 (0-1), 默认 0
        hpss_harmonic_ratio: HPSS 谐波分量能量比 (0-1), 默认 0.30
    """
    hnr: float = 0.0
    cpp: float = 0.0
    spectral_tilt: float = -10.0
    voicing_ratio: float = 0.0
    detection_confidence: float = 0.0
    is_mixed_audio: bool = False
    mixed_audio_confidence: float = 0.0
    hpss_harmonic_ratio: float = 0.30

    def __post_init__(self):
        # Validate ranges for fields that have meaningful physical constraints
        # HNR: theoretical range 0-40 dB for vocal signals
        # CPP: practical range 0-10
        # Spectral tilt: practical range -20 to +10 dB/oct
        # Voicing ratio, confidence: 0-1
        # HPSS ratio: 0-1
        # All are validated softly — extreme values are clamped at extraction time,
        # not at construction time, since defaults are intentionally out of range
        pass
