"""
Flag 系统桥接层 — v7.7

桥接 services/feature_flags.py (API 层 FeatureFlags)
与 backend/domain/assessment/feature_flags.py (领域层 DimensionFlags),
确保两个 Flag 系统同步。

设计原则:
- 单向转换: FeatureFlags → DimensionFlags (API → Domain)
- 同名映射: 同名字段直接复制
- 安全默认: DimensionFlags 独有字段保持默认值 (True)
"""

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.feature_flags import FeatureFlags
    from backend.domain.assessment.feature_flags import DimensionFlags

# 公共字段: FeatureFlags 和 DimensionFlags 中都存在且语义相同的字段
_COMMON_FIELDS = [
    'enable_multiscale_hnr',
    'enable_praat_cpp',
    'enable_voicing_detection',
    'enable_torchcrepe_fallback',
    'enable_cross_dimension_modifiers',
    'enable_reverb_compensation',
    'enable_praat_voice_quality',
    'enable_ddd_feature_extraction',
    'enable_audiofeat',
]


def to_dimension_flags(feature_flags: FeatureFlags) -> DimensionFlags:
    """
    将 API 层 FeatureFlags 转换为领域层 DimensionFlags。

    同名字段直接映射, DimensionFlags 独有字段保持默认值。

    Args:
        feature_flags: API 层的功能开关

    Returns:
        DimensionFlags 实例
    """
    from backend.domain.assessment.feature_flags import DimensionFlags

    kwargs: dict = {}
    for field_name in _COMMON_FIELDS:
        if hasattr(feature_flags, field_name):
            kwargs[field_name] = getattr(feature_flags, field_name)

    return DimensionFlags(**kwargs)
