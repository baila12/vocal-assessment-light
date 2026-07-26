"""
共享数学工具函数 — v7.2.1

提取重复的安全转换函数，消除 feature_adapters / muscle_extractor / timbre_extractor
等模块中的代码重复。
"""
from __future__ import annotations
import math


def safe_float(value, default: float = 0.0) -> float:
    """安全转换为 float，NaN/Inf/None 回退到默认值"""
    if value is None:
        return default
    try:
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except (TypeError, ValueError):
        return default


def safe_clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """安全 clamp 到 [lo, hi] 区间"""
    return max(lo, min(hi, safe_float(value, default=lo)))


__all__ = ["safe_float", "safe_clamp"]
