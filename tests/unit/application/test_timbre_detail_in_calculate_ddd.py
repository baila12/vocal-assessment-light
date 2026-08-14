"""
P2-15 Phase 2 — calculate_ddd 完整音色 dict 契约

旧 legacy TimbreService.analyze (pro 模式) 用不同公式重算 brightness/HNR/vibrato,
与 DDD TimbreAdjuster 形成"音色计算两遍"。本测试断言 calculate_ddd 输出
`timbre_detail` (保持旧 TimbreResult 9 键契约), 由 DDD 产物组装:
  brightness/warmth/nasality ← ta 质量分 /100
  hnr ← audiofeat.hnr_mean (无则 technique.hnr_mean)
  breathiness ← audiofeat.spectral_flatness_mean proxy
  vibrato_rate ← technique.vibrato_rate_avg
  vibrato_extent/vibrato_count ← DDD 无等价物占位 0
"""

import pytest

from backend.application.assessment.scoring_orchestrator import ScoringOrchestrator
from backend.domain.assessment.timbre_adjuster import TimbreAdjuster, TimbreFeatures
from backend.domain.assessment.technique_scorer import TechniqueFeatures
from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures


TIMBRE_DETAIL_KEYS = (
    "brightness", "warmth", "nasality", "breathiness", "hnr",
    "vibrato_rate", "vibrato_extent", "vibrato_count", "style",
)


def _make_inputs():
    """构造 DDD 提取 + 评分输入 (audiofeat 增强路径触发)"""
    timbre = TimbreFeatures(
        spectral_centroid_deviation=0.2,
        mfcc_cluster_distance=0.4,
        mfcc_cluster_purity=0.85,
        harmonic_richness=0.6,
        nasality_index=0.2,
        harmonic_stability=70.0,
    )
    audiofeat = AudiofeatFeatures(
        spectral_centroid_mean=1800.0,
        harmonic_richness=0.6,
        nasality=0.15,
        spectral_roughness=0.3,
        hnr_mean=25.0,
        spectral_flatness_mean=0.35,
    )
    technique = TechniqueFeatures(
        hnr_mean=15.0,
        vibrato_rate_avg=5.5,
        vibrato_quality=70.0,
    )
    return timbre, audiofeat, technique


class TestTimbreDetailInCalculateDdd:
    def test_nine_keys_present(self):
        """timbre_detail 保持旧 TimbreResult 9 键契约"""
        timbre, audiofeat, technique = _make_inputs()
        result = ScoringOrchestrator().calculate_ddd(
            timbre=timbre, audiofeat=audiofeat, technique=technique,
        )
        detail = result["timbre_detail"]
        for key in TIMBRE_DETAIL_KEYS:
            assert key in detail, f"timbre_detail 应含 {key}, 实际 keys={list(detail.keys())}"

    def test_brightness_warmth_nasality_from_ta_scores(self):
        """brightness/warmth/nasality == ta 质量分 / 100 (0-1)"""
        timbre, audiofeat, _ = _make_inputs()
        ta = TimbreAdjuster().calculate(timbre, audiofeat=audiofeat)
        result = ScoringOrchestrator().calculate_ddd(
            timbre=timbre, audiofeat=audiofeat, technique=_make_inputs()[2],
        )
        detail = result["timbre_detail"]
        assert detail["brightness"] == round(ta.brightness_score / 100.0, 3)
        assert detail["warmth"] == round(ta.warmth_score / 100.0, 3)
        assert detail["nasality"] == round(ta.nasality_score / 100.0, 3)
        for key in ("brightness", "warmth", "nasality"):
            assert 0.0 <= detail[key] <= 1.0

    def test_hnr_prefers_audiofeat(self):
        """audiofeat.hnr_mean > 0 时优先取 audiofeat"""
        timbre, audiofeat, technique = _make_inputs()
        result = ScoringOrchestrator().calculate_ddd(
            timbre=timbre, audiofeat=audiofeat, technique=technique,
        )
        assert result["timbre_detail"]["hnr"] == 25.0

    def test_hnr_falls_back_to_technique(self):
        """audiofeat.hnr_mean == 0 时回退 technique.hnr_mean"""
        timbre, _, _ = _make_inputs()
        audiofeat_no_hnr = AudiofeatFeatures(spectral_centroid_mean=0.0)  # 无有效数据
        technique = TechniqueFeatures(hnr_mean=18.0, vibrato_rate_avg=0.0)
        result = ScoringOrchestrator().calculate_ddd(
            timbre=timbre, audiofeat=audiofeat_no_hnr, technique=technique,
        )
        assert result["timbre_detail"]["hnr"] == 18.0

    def test_vibrato_rate_from_technique(self):
        """vibrato_rate 取自 technique.vibrato_rate_avg"""
        timbre, audiofeat, technique = _make_inputs()
        result = ScoringOrchestrator().calculate_ddd(
            timbre=timbre, audiofeat=audiofeat, technique=technique,
        )
        assert result["timbre_detail"]["vibrato_rate"] == 5.5

    def test_vibrato_extent_count_placeholders(self):
        """DDD 无 vibrato_extent/count 等价物 → 占位 0"""
        timbre, audiofeat, technique = _make_inputs()
        result = ScoringOrchestrator().calculate_ddd(
            timbre=timbre, audiofeat=audiofeat, technique=technique,
        )
        detail = result["timbre_detail"]
        assert detail["vibrato_extent"] == 0.0
        assert detail["vibrato_count"] == 0

    def test_style_tag_non_empty(self):
        """style 标签非空字符串"""
        timbre, audiofeat, technique = _make_inputs()
        result = ScoringOrchestrator().calculate_ddd(
            timbre=timbre, audiofeat=audiofeat, technique=technique,
        )
        assert isinstance(result["timbre_detail"]["style"], str)
        assert result["timbre_detail"]["style"]

    def test_none_inputs_safe(self):
        """全部特征 None → timbre_detail 仍含 9 键且不崩溃 (ta 默认回退)"""
        result = ScoringOrchestrator().calculate_ddd()
        detail = result["timbre_detail"]
        for key in TIMBRE_DETAIL_KEYS:
            assert key in detail
        assert detail["brightness"] == 0.0
        assert detail["hnr"] == 0.0

    def test_does_not_affect_timbre_adjustment(self):
        """timbre_detail 为附加输出, 不改变 timbre_adjustment 评分"""
        timbre, audiofeat, technique = _make_inputs()
        ta = TimbreAdjuster().calculate(timbre, audiofeat=audiofeat)
        result = ScoringOrchestrator().calculate_ddd(
            timbre=timbre, audiofeat=audiofeat, technique=technique,
        )
        assert result["timbre_adjustment"] == pytest.approx(ta.adjustment, rel=1e-6)
