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
    功能开关集合 — v5.18 实验功能, v6.2 默认启用已验证算法

    Fields:
        enable_multiscale_hnr: 多尺度 HNR (短/中/长窗 + 稳定性) — de Krom 1993
        enable_praat_cpp: Praat CPP via parselmouth — 替换手动 FFT 倒谱
        enable_voicing_detection: Voicing detection 评估 — 召回率/误报率
        enable_torchcrepe_fallback: TorchCREPE 备选接入 — PYIN 降级时启用
        enable_cross_dimension_modifiers: v5.19 跨维度集成 (HNR稳定性→气息, Voicing→音准)
        enable_reverb_compensation: v5.20 混响补偿 (HPSS+谱减法 → HNR/CPP修正)
        enable_praat_voice_quality: v6.2 Praat 声质特征 (jitter/shimmer/formants/spectral_tilt)
    """
    # v6.2: 所有已验证的高级算法默认启用
    # de Krom (1993) 四频带 HNR — 替换 HPSS 简化版
    enable_multiscale_hnr: bool = True
    # VoiceLab Praat PowerCepstrum CPP — 替换手动 FFT 倒谱
    enable_praat_cpp: bool = True
    # PYIN voicing 自一致性评估
    enable_voicing_detection: bool = True
    # TorchCREPE 备选 f0 提取 (PYIN 检测率 < 50% 时启用)
    enable_torchcrepe_fallback: bool = True
    # v5.19 跨维度修正: HNR稳定性→气息, Voicing→音准可信度
    enable_cross_dimension_modifiers: bool = True
    # v5.20 混响补偿 (HPSS + Boll 1979 谱减法)
    enable_reverb_compensation: bool = True
    # v6.2 Praat 声质特征 (jitter/shimmer/formants/spectral_tilt)
    # Baken & Orlikoff (2000), Sundberg (1987)
    enable_praat_voice_quality: bool = True

    @classmethod
    def for_quick(cls) -> 'FeatureFlags':
        """Quick 模式: 快速特征优先, 关闭耗时但低收益的算法"""
        return cls(
            enable_multiscale_hnr=False,  # 多频带 HNR 开销大, Quick 跳过
            enable_praat_cpp=True,
            enable_voicing_detection=True,
            enable_torchcrepe_fallback=True,
            enable_cross_dimension_modifiers=True,
            enable_reverb_compensation=False,  # 混响补偿开销大, Quick 跳过
            enable_praat_voice_quality=True,  # v6.2: 已截断到 60s, 可接受
        )

    @classmethod
    def for_professional(cls) -> 'FeatureFlags':
        """Pro 模式: 启用所有高级算法"""
        return cls(
            enable_multiscale_hnr=True,
            enable_praat_cpp=True,
            enable_voicing_detection=True,
            enable_torchcrepe_fallback=True,
            enable_cross_dimension_modifiers=True,
            enable_reverb_compensation=True,
            enable_praat_voice_quality=True,
        )

    @classmethod
    def safe_baseline(cls) -> 'FeatureFlags':
        """安全基线: 全部关闭, 用于回归测试"""
        return cls(
            enable_multiscale_hnr=False,
            enable_praat_cpp=False,
            enable_voicing_detection=False,
            enable_torchcrepe_fallback=False,
            enable_cross_dimension_modifiers=False,
            enable_reverb_compensation=False,
            enable_praat_voice_quality=False,
        )
