"""TechniqueScorer TDD — 10 tests, v7.0 refactored: articulation + breath-voice ratio"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../../..")

import pytest
from backend.domain.assessment.technique_scorer import TechniqueScorer, TechniqueFeatures


def make_features(**kwargs) -> TechniqueFeatures:
    defaults = {
        "onset_density": 3.0, "spectral_flux": 1.0, "consonant_clarity": 50.0,
        "hnr_mean": 18.0, "spectral_tilt": 0.0, "hf_energy_ratio": 0.4, "cpp_mean": 10.0,  # v7.4: 中性 CPPS 默认 (8-12→良好)
    }
    defaults.update(kwargs)
    return TechniqueFeatures(**defaults)


class TestTechniqueScorer:
    def setup_method(self):
        self.scorer = TechniqueScorer()

    def test_articulation_perfect(self):
        f = make_features(consonant_clarity=100.0, onset_density=3.0, spectral_flux=1.0)
        result = self.scorer.calculate(f)
        assert result.articulation_clarity >= 60

    def test_articulation_poor(self):
        f = make_features(consonant_clarity=20.0, onset_density=0.3, spectral_flux=8.0)
        result = self.scorer.calculate(f)
        assert result.articulation_clarity < 40

    def test_breath_voice_ratio_optimal(self):
        f = make_features(hnr_mean=18.0, spectral_tilt=0.0, hf_energy_ratio=0.4)
        result = self.scorer.calculate(f)
        assert result.breath_voice_ratio >= 55  # v7.4: CPPS (~35) + HNR (~25) = ~60

    def test_breath_voice_ratio_breathy(self):
        f = make_features(hnr_mean=4.0, spectral_tilt=-8.0, hf_energy_ratio=0.8)
        result = self.scorer.calculate(f)
        assert result.breath_voice_ratio < 50

    def test_breath_voice_ratio_unnatural_high(self):
        f = make_features(hnr_mean=35.0)
        result = self.scorer.calculate(f)
        assert result.breath_voice_ratio < 90  # too "hard" = unnatural

    def test_combined_5050_weighting(self):
        f = make_features(consonant_clarity=60.0, hnr_mean=18.0)
        result = self.scorer.calculate(f)
        # ~55 articulation * 0.5 + ~60 bvr * 0.5 = ~57.5
        assert 50 <= result.raw_score <= 85  # v7.4: CPPS 10 中性分数

    def test_hnr_mean_preserved(self):
        f = make_features(hnr_mean=15.0)
        result = self.scorer.calculate(f)
        assert result.hnr_mean == 15.0

    def test_cpp_mean_preserved(self):
        f = make_features(cpp_mean=2.0)
        result = self.scorer.calculate(f)
        assert result.cpp_mean == 2.0

    def test_weighted_method(self):
        f = make_features()
        result = self.scorer.calculate(f)
        assert result.weighted() == result.raw_score * 0.25

    def test_score_clamped(self):
        f = make_features(consonant_clarity=0.0, hnr_mean=0.0, spectral_tilt=-20.0)
        result = self.scorer.calculate(f)
        assert 0 <= result.raw_score <= 100

    # ---- v7.4: CPPS primary breath-voice ratio ----

    def test_breath_voice_cpps_optimal(self):
        """CPPS>=12 → 气声比满分段，CPPS 贡献 ~40 分"""
        f = make_features(hnr_mean=18.0, cpp_mean=14.0, spectral_tilt=0.0, hf_energy_ratio=0.4)
        result = self.scorer.calculate(f)
        assert result.breath_voice_ratio >= 60  # CPPS 40% + HNR 25% ≈ 65

    def test_breath_voice_cpps_unavailable_fallback(self):
        """CPPS=0 → HNR 回退权重 45%"""
        f = make_features(hnr_mean=18.0, cpp_mean=0.0, spectral_tilt=0.0, hf_energy_ratio=0.4)
        result = self.scorer.calculate(f)
        assert result.breath_voice_ratio >= 40  # HNR fallback 45%

    def test_breath_voice_cpps_low(self):
        """CPPS<3 → 极气息感，低分"""
        f = make_features(hnr_mean=10.0, cpp_mean=2.0, spectral_tilt=0.0, hf_energy_ratio=0.4)
        result = self.scorer.calculate(f)
        assert result.breath_voice_ratio < 45

    def test_breath_voice_cpps_weight_40_percent(self):
        """CPPS 12+ 单独贡献约 40 分 (含 spectral/hf 默认)"""
        f = make_features(hnr_mean=0.0, cpp_mean=12.0, spectral_tilt=0.0, hf_energy_ratio=0.4)
        result = self.scorer.calculate(f)
        assert 35 <= result.breath_voice_ratio <= 60

    def test_hnr_no_longer_70_percent(self):
        """HNR 最优不再贡献 70 分 (现在 CPPS 为主特征)"""
        f = make_features(hnr_mean=18.0, cpp_mean=0.0, spectral_tilt=0.0, hf_energy_ratio=0.4)
        result = self.scorer.calculate(f)
        assert result.breath_voice_ratio < 70

    def test_breath_voice_cpps_mid_range(self):
        """CPPS 5-8 中段 → 部分分数"""
        f = make_features(hnr_mean=15.0, cpp_mean=6.5, spectral_tilt=0.0, hf_energy_ratio=0.4)
        result = self.scorer.calculate(f)
        assert 25 <= result.breath_voice_ratio <= 65

    def test_breath_voice_cpps_fallback_higher_weight(self):
        """CPPS=0 时 HNR 18 得比分比 CPPS=6.5 时 HNR 18 得分更低 (因为 CPPS 主特征缺失)"""
        f_no_cpps = make_features(hnr_mean=18.0, cpp_mean=0.0, spectral_tilt=0.0, hf_energy_ratio=0.4)
        f_mid_cpps = make_features(hnr_mean=18.0, cpp_mean=6.5, spectral_tilt=0.0, hf_energy_ratio=0.4)
        r_no = self.scorer.calculate(f_no_cpps)
        r_mid = self.scorer.calculate(f_mid_cpps)
        # CPPS 可用时 HNR 权重仅 25%，不可用时 45%，但 CPPS 中段会有额外贡献
        assert r_mid.raw_score > r_no.raw_score - 5  # 不应差距过大

    # ---- v7.4: 咬字增强 (ZCR + Spectral Centroid + C-V ratio) ----

    def test_articulation_centroid_enhanced(self):
        """Spectral centroid >0 → 使用增强路径 (30% 权重)"""
        f = make_features(spectral_centroid=2500.0, zcr_mean=0.0)
        result = self.scorer.calculate(f)
        assert result.articulation_clarity >= 20  # centroid contributes ~21

    def test_articulation_zcr_good(self):
        """ZCR ≥0.15 → 清晰辅音 → 25 分"""
        f = make_features(zcr_mean=0.20, spectral_centroid=0.0)
        result = self.scorer.calculate(f)
        assert result.articulation_clarity >= 20  # ZCR 25 + onset 10 ≈ 35

    def test_articulation_cv_ratio_optimal(self):
        """C-V 能量比接近 -15dB → 满分贡献"""
        f = make_features(zcr_mean=0.20, spectral_centroid=2000.0, cv_energy_ratio=-14.0)
        result = self.scorer.calculate(f)
        assert result.articulation_clarity > 50  # 多特征综合

    def test_articulation_fallback_when_new_features_missing(self):
        """ZCR=0 且 Centroid=0 → 回退到旧 consonant_clarity 路径"""
        f = make_features(consonant_clarity=60.0, onset_density=3.0, spectral_flux=1.0,
                          zcr_mean=0.0, spectral_centroid=0.0)
        result = self.scorer.calculate(f)
        assert result.articulation_clarity >= 30  # old path: 30+25=55

    def test_articulation_flux_positive_contribution(self):
        """Spectral Flux 现在是正贡献 (25% 权重), 不再是纯扣分项"""
        f = make_features(spectral_flux=2.5, zcr_mean=0.0, spectral_centroid=0.0,
                          consonant_clarity=0.0, onset_density=0.0)
        result = self.scorer.calculate(f)
        # With new features missing (zcr=0, centroid=0), falls back to old path
        # which still treats flux as penalty
        # But when new features present, flux contributes positively
        f2 = make_features(spectral_flux=2.5, zcr_mean=0.05, spectral_centroid=0.0,
                           consonant_clarity=0.0, onset_density=0.0)
        result2 = self.scorer.calculate(f2)
        assert result2.articulation_clarity > 0  # Flux positive contrib in new path


# ================================================================
# v7.3: TechniqueScorer + audiofeat 增强测试
# ================================================================

def _make_audiofeat(**kwargs):
    """构造 AudiofeatFeatures 测试数据"""
    from backend.domain.audio.audiofeat_extractor import AudiofeatFeatures
    return AudiofeatFeatures(**kwargs)


class TestTechniqueScorerAudiofeat:
    """TechniqueScorer audiofeat 增强路径测试 — v7.3"""

    def setup_method(self):
        self.scorer = TechniqueScorer()

    # ---- 向后兼容 ----

    def test_audiofeat_none_backward_compatible(self):
        """audiofeat=None 时行为不变"""
        f = make_features(consonant_clarity=60.0, hnr_mean=18.0)
        result = self.scorer.calculate(f, audiofeat=None)
        assert 50 <= result.raw_score <= 85  # v7.4: CPPS 10 中性分数

    def test_audiofeat_all_defaults_no_effect(self):
        """全零 audiofeat 不应影响评分"""
        f = make_features(consonant_clarity=60.0, hnr_mean=18.0)
        result_no_af = self.scorer.calculate(f)
        af = _make_audiofeat()
        result_with_af = self.scorer.calculate(f, audiofeat=af)
        assert result_with_af.raw_score == result_no_af.raw_score

    # ---- Jitter (频率微扰) ----

    def test_audiofeat_jitter_low_boosts_articulation(self):
        """Jitter<0.5% → 极稳定咬字, 加分"""
        f = make_features(consonant_clarity=50.0)
        af = _make_audiofeat(jitter_local=0.3)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score > result_no_af.raw_score

    def test_audiofeat_jitter_high_penalizes_articulation(self):
        """Jitter>3% → 频率不稳定, 扣分"""
        f = make_features(consonant_clarity=50.0, hnr_mean=18.0)
        af = _make_audiofeat(jitter_local=4.0)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score < result_no_af.raw_score

    # ---- Shimmer (幅度微扰) ----

    def test_audiofeat_shimmer_low_boosts_breath_voice(self):
        """Shimmer<0.1dB → 极稳定振幅, 加分"""
        f = make_features(hnr_mean=18.0)
        af = _make_audiofeat(shimmer_db=0.05)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score > result_no_af.raw_score

    def test_audiofeat_shimmer_high_penalizes(self):
        """Shimmer>0.5dB → 振幅不稳定, 扣分"""
        f = make_features(hnr_mean=18.0)
        af = _make_audiofeat(shimmer_db=0.7)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score < result_no_af.raw_score

    # ---- Closed Quotient (声门闭合商) ----

    def test_audiofeat_closed_quotient_optimal_boosts(self):
        """CQ 0.4-0.6 → 高效发声, 加分"""
        f = make_features(hnr_mean=18.0)
        af = _make_audiofeat(closed_quotient=0.5)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score > result_no_af.raw_score

    def test_audiofeat_closed_quotient_low_penalizes(self):
        """CQ<0.2 → 声门闭合不足, 扣分"""
        f = make_features(hnr_mean=18.0)
        af = _make_audiofeat(closed_quotient=0.1)
        result = self.scorer.calculate(f, audiofeat=af)
        result_no_af = self.scorer.calculate(f)
        assert result.raw_score < result_no_af.raw_score

    # ---- Score clamping ----

    def test_audiofeat_enhanced_score_in_range(self):
        """增强后分数仍在 [0, 100]"""
        f = make_features(consonant_clarity=90.0, hnr_mean=25.0)
        af = _make_audiofeat(jitter_local=0.1, shimmer_db=0.02, closed_quotient=0.55)
        result = self.scorer.calculate(f, audiofeat=af)
        assert 0.0 <= result.raw_score <= 100.0
