"""
Feature Flag 机制 v5.18

控制实验性功能的启用/禁用。所有新算法通过 Feature Flag 默认关闭，
经独立验证后方可逐一开启。

设计原则:
- 默认全部关闭: 确保已有评分管线零影响
- 单一入口: 通过 analyze_and_score() 传入，贯穿全链路
- 性能优先: 属性访问 O(1)，无外部依赖

使用方式:
    from services.feature_flags import FeatureFlags

    flags = FeatureFlags()                        # 全部关闭
    flags.enable_multiscale_hnr = True           # 开启多尺度HNR
    result = analyze_and_score(filepath, feature_flags=flags)
"""
from dataclasses import dataclass


@dataclass
class FeatureFlags:
    """
    功能开关集合 — v5.18 实验功能

    所有 flag 默认 False，验证后设为 True 启用。

    Fields:
        enable_multiscale_hnr: 多尺度 HNR (短/中/长窗 + 稳定性) — de Krom 1993
        enable_praat_cpp: Praat CPP via parselmouth — 替换手动 FFT 倒谱
        enable_voicing_detection: Voicing detection 评估 — 召回率/误报率
        enable_torchcrepe_fallback: TorchCREPE 备选接入 — PYIN 降级时启用
        enable_cross_dimension_modifiers: v5.19 跨维度集成 (HNR稳定性→气息, Voicing→音准)
    """
    enable_multiscale_hnr: bool = False
    enable_praat_cpp: bool = False
    enable_voicing_detection: bool = False
    enable_torchcrepe_fallback: bool = False
    enable_cross_dimension_modifiers: bool = False  # v5.19
