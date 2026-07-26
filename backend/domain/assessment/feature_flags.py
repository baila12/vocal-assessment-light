"""
六维评分 Feature Flag 独立开关

每个维度单一职责、零依赖 — 关一个不影响其余。
保留 v6.2 高级算法开关 (7 个，全默认启用)。
"""

from __future__ import annotations
from dataclasses import dataclass


@dataclass
class DimensionFlags:
    """六维独立开关"""

    # ===== 维度级 =====
    enable_pitch: bool = True
    enable_rhythm: bool = True
    enable_breath: bool = True
    enable_technique: bool = True           # 咬字 + 气声比
    enable_muscle_strength: bool = True     # NEW ⚠️ 启发式
    enable_artistry: bool = True
    enable_timbre_adjustment: bool = True   # NEW ⚠️ 启发式
    enable_vnext_weights: bool = True       # False = 回退旧五维权重

    # ===== v7.1.2: DDD 原生特征提取 =====
    enable_ddd_feature_extraction: bool = True   # True = 绕过旧 AudioFeaturesService, 直接使用 7 个 DDD 提取器

    # ===== 子维度级 =====
    enable_articulation: bool = True        # 咬字清晰度
    enable_breath_voice_ratio: bool = True  # 气声比
    enable_body_muscle: bool = True         # 身体肌肉
    enable_facial_muscle: bool = True       # 面部肌肉

    # ===== v7.2: audiofeat 增强特征提取 =====
    enable_audiofeat: bool = False           # True = 启用 audiofeat 130+ 声学特征 (CPPS/GNE/等)

    # ===== v6.2 高级算法开关 (保留) =====
    enable_multiscale_hnr: bool = True
    enable_praat_cpp: bool = True
    enable_voicing_detection: bool = True
    enable_torchcrepe_fallback: bool = True
    enable_cross_dimension_modifiers: bool = True
    enable_reverb_compensation: bool = True
    enable_praat_voice_quality: bool = True
