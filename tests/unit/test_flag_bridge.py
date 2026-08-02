"""
Flag 桥接层单元测试 — v7.7

测试 FeatureFlags → DimensionFlags 转换, 确保两个 Flag 系统正确同步。
"""

import pytest
from services.feature_flags import FeatureFlags
from backend.shared.flag_bridge import to_dimension_flags


class TestFlagBridge:
    """Flag 桥接转换测试"""

    def test_for_quick_enables_audiofeat(self):
        """Quick 模式应启用 audiofeat 增强特征"""
        ff = FeatureFlags.for_quick()
        df = to_dimension_flags(ff)

        assert df.enable_audiofeat is True, "Quick 模式应启用 audiofeat"
        assert df.enable_multiscale_hnr is False, "Quick 模式应禁用多尺度 HNR"
        assert df.enable_reverb_compensation is False, "Quick 模式应禁用混响补偿"

    def test_for_professional_enables_all(self):
        """Professional 模式应启用所有高级算法"""
        ff = FeatureFlags.for_professional()
        df = to_dimension_flags(ff)

        assert df.enable_audiofeat is True, "Professional 模式应启用 audiofeat"
        assert df.enable_multiscale_hnr is True
        assert df.enable_praat_cpp is True
        assert df.enable_reverb_compensation is True

    def test_safe_baseline_all_disabled(self):
        """安全基线应全部关闭"""
        ff = FeatureFlags.safe_baseline()
        df = to_dimension_flags(ff)

        assert df.enable_audiofeat is False
        assert df.enable_multiscale_hnr is False
        assert df.enable_praat_cpp is False
        assert df.enable_ddd_feature_extraction is False

    def test_custom_flags_mapped_correctly(self):
        """自定义 flags 应正确映射"""
        ff = FeatureFlags()
        ff.enable_audiofeat = True
        ff.enable_multiscale_hnr = False
        ff.enable_fcpe = True

        df = to_dimension_flags(ff)

        assert df.enable_audiofeat is True
        assert df.enable_multiscale_hnr is False
        # enable_fcpe 只在 FeatureFlags 中存在, 不应映射到 DimensionFlags

    def test_dimension_flags_keep_sensible_defaults(self):
        """维度级开关应保持默认值 (True), 不被 FeatureFlags 覆盖"""
        ff = FeatureFlags()  # 全部默认
        df = to_dimension_flags(ff)

        # 维度级开关在 DimensionFlags 中, FeatureFlags 没有对应字段
        # 应保持 DimensionFlags 的默认值 (True)
        assert df.enable_pitch is True
        assert df.enable_rhythm is True
        assert df.enable_breath is True
        assert df.enable_technique is True
        assert df.enable_artistry is True
        assert df.enable_timbre_adjustment is True
        assert df.enable_vnext_weights is True
        assert df.enable_articulation is True
        assert df.enable_breath_voice_ratio is True
        assert df.enable_body_muscle is True
        assert df.enable_facial_muscle is True

    def test_all_common_fields_mapped(self):
        """验证所有同名公共字段都被正确映射"""
        ff = FeatureFlags()
        # 设置所有公共字段为非默认值以验证映射
        ff.enable_multiscale_hnr = False
        ff.enable_praat_cpp = False
        ff.enable_voicing_detection = False
        ff.enable_torchcrepe_fallback = False
        ff.enable_cross_dimension_modifiers = False
        ff.enable_reverb_compensation = False
        ff.enable_praat_voice_quality = False
        ff.enable_ddd_feature_extraction = False
        ff.enable_audiofeat = False

        df = to_dimension_flags(ff)

        # 所有应为 False
        assert df.enable_multiscale_hnr is False
        assert df.enable_praat_cpp is False
        assert df.enable_voicing_detection is False
        assert df.enable_torchcrepe_fallback is False
        assert df.enable_cross_dimension_modifiers is False
        assert df.enable_reverb_compensation is False
        assert df.enable_praat_voice_quality is False
        assert df.enable_ddd_feature_extraction is False
        assert df.enable_audiofeat is False
