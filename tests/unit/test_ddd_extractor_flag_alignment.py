"""
P2-15 Phase 5.2 — DDD 提取器 flag 对齐

audio_analysis.py 的 `_ddd_feature_extractor` 硬编码 enable_audiofeat=True;
生产路由传 for_quick/for_professional。本测试断言:
  - feature_flags=None → 模块级默认 (等价 to_dimension_flags(FeatureFlags()), 数值不变)
  - for_quick → DDD 提取器关闭 multiscale_hnr/reverb (quick 声学设置)
  - for_professional → 全真 (与硬编码等价)
"""

import pytest

from api.business.audio_analysis import _resolve_ddd_extractor, _ddd_feature_extractor
from services.feature_flags import FeatureFlags
from backend.shared.flag_bridge import to_dimension_flags
from backend.domain.assessment.feature_flags import DimensionFlags
from backend.application.assessment.ddd_feature_orchestrator import (
    DddFeatureExtractionOrchestrator,
)


class TestResolveDddExtractor:
    def test_none_returns_module_default(self):
        """feature_flags=None → 模块级默认提取器 (真实音频回归路径, 数值不变)"""
        assert _resolve_ddd_extractor(None) is _ddd_feature_extractor

    def test_none_path_is_orchestrator(self):
        """模块级默认仍是 DddFeatureExtractionOrchestrator 实例 (test_ddd_extraction_flag 兼容)"""
        assert isinstance(_resolve_ddd_extractor(None), DddFeatureExtractionOrchestrator)

    def test_default_flags_equivalent_to_hardcoded(self):
        """to_dimension_flags(FeatureFlags()) == 硬编码 DimensionFlags(enable_audiofeat=True)"""
        default_flags = to_dimension_flags(FeatureFlags())
        hardcoded = DimensionFlags(enable_audiofeat=True)
        assert default_flags == hardcoded, (
            "None 路径 flag 与旧硬编码漂移 — 会导致真实音频回归评分变化"
        )

    def test_for_quick_honors_quick_flags(self):
        """for_quick → 关闭 multiscale_hnr/reverb, 保留 audiofeat"""
        extractor = _resolve_ddd_extractor(FeatureFlags.for_quick())
        flags = extractor._flags
        assert flags.enable_audiofeat is True
        assert flags.enable_multiscale_hnr is False
        assert flags.enable_reverb_compensation is False

    def test_for_professional_full_flags(self):
        """for_professional → 全真 (与硬编码等价, pro 评分不变)"""
        extractor = _resolve_ddd_extractor(FeatureFlags.for_professional())
        flags = extractor._flags
        assert flags.enable_audiofeat is True
        assert flags.enable_multiscale_hnr is True
        assert flags.enable_reverb_compensation is True
        assert flags.enable_praat_cpp is True

    def test_explicit_flags_produce_orchestrator(self):
        """显式 flags → 新 DddFeatureExtractionOrchestrator 实例"""
        extractor = _resolve_ddd_extractor(FeatureFlags.for_quick())
        assert isinstance(extractor, DddFeatureExtractionOrchestrator)
        assert extractor is not _ddd_feature_extractor
