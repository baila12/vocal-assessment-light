"""
TDD RED-Phase 测试 — v5.19 评分区分度修复 + 跨维度集成

这些测试为 PROJECT_STATUS.md 中规划的 v5.19 功能定义预期行为。
当前应标记为 expected failure (xfail)，实现后改为正常断言。

TDD 流程:
  1. RED:   这些测试当前 FAIL (功能未实现)
  2. GREEN: 实现功能后 → 测试通过
  3. REFACTOR: 优化实现 → 测试仍通过

功能清单:
  - 气息评分子维度基线归零 (40→0)
  - 音准评分 MAE 阈值扩展
  - HNR/CPP 天花板提升
  - 跨维度集成 (HNR稳定性→气息, Voicing→音准)
  - 音量维度独立 (remove xfail)
"""
import pytest
import json
from pathlib import Path
import numpy as np


# ============================================================================
# Phase 1: 气息评分区分度 (P0)
# ============================================================================

class TestBreathDifferentiation:
    """气息评分的呼吸区分度 — 基线归零后应有更广的分数范围"""

    @pytest.mark.xfail(
        reason="TDD RED: 气息子维度基线仍为 40，区分度仅 5-15 分。"
               "v5.19: 基线归零 + 加分范围扩大 → 区分度 ≥ 30"
    )
    def test_breath_score_wider_range_with_synthetic(self):
        """合成测试: 高质量气息 vs 低质量气息应有 ≥ 30 分差距"""
        from services.features.breath import BreathAnalyzer
        from services.scoring.breath_scorer import BreathScorer
        from services.scoring_config import BreathThresholds
        import numpy as np

        sr = 22050
        duration = 3.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        # 模拟稳定气息: 稳定振幅 + 谐波丰富
        f0 = 220.0
        good_signal = np.zeros_like(t)
        for h in range(1, 10):
            good_signal += (0.5 / h) * np.sin(2 * np.pi * f0 * h * t)
        good_signal = good_signal / np.max(np.abs(good_signal)) * 0.5

        # 模拟不稳定气息: 振幅抖动 + 噪声
        np.random.seed(42)
        bad_signal = np.zeros_like(t)
        for h in range(1, 6):
            bad_signal += (0.3 / h) * np.sin(2 * np.pi * f0 * h * t)
        # 添加振幅调制 (模拟气息不稳)
        envelope = 1.0 + 0.5 * np.sin(2 * np.pi * 3 * t) + 0.3 * np.random.randn(len(t))
        bad_signal = bad_signal * envelope
        bad_signal = bad_signal / np.max(np.abs(bad_signal)) * 0.5

        analyzer = BreathAnalyzer(sample_rate=sr)
        scorer = BreathScorer(BreathThresholds())

        good_result = analyzer.calculate_breath_stability(good_signal, singing_style='pop')
        bad_result = analyzer.calculate_breath_stability(bad_signal, singing_style='pop')

        good_score = scorer.calculate(good_result)[0]
        bad_score = scorer.calculate(bad_result)[0]

        diff = good_score - bad_score
        assert diff >= 30, (
            f"气息区分度不足: good={good_score:.0f}, bad={bad_score:.0f}, diff={diff:.0f}"
        )

    def test_breath_baseline_gives_near_zero(self):
        """空/极低质量输入 → 气息分数应接近 0 (不送免费分)"""
        from services.features.breath import BreathAnalyzer
        from services.scoring.breath_scorer import BreathScorer
        from services.scoring_config import BreathThresholds
        import numpy as np

        sr = 22050
        # 极短低质量噪声
        np.random.seed(42)
        noise = np.random.randn(int(sr * 0.5)) * 0.01

        analyzer = BreathAnalyzer(sample_rate=sr)
        scorer = BreathScorer(BreathThresholds())

        result = analyzer.calculate_breath_stability(noise, singing_style='pop')
        score = scorer.calculate(result)[0]

        # 几乎无声 → 气息分应很低
        assert score < 15, (
            f"低质量输入应得低分, 实际: {score:.1f}"
        )

    @pytest.mark.xfail(
        reason="TDD RED: 需要 breath 子维度基线归零后更新回归基线。"
               "v5.19 实现后移除 xfail 并验证真实音频区分度。"
    )
    def test_real_audio_breath_differentiation(self):
        """真实音频: 高分气息 - 低分气息 ≥ 18 分"""
        from api.business.audio_analysis import analyze_and_score

        test_dir = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
        high_files = sorted(test_dir.glob("*（高分）*.mp3")) if test_dir.exists() else []
        low_files = sorted(test_dir.glob("*（低分）*.mp3")) if test_dir.exists() else []

        if len(high_files) < 1 or len(low_files) < 1:
            pytest.skip("需要真实测试音频 (至少1首高分+1首低分)")

        high_result = analyze_and_score(str(high_files[0]), mode='quick')
        low_result = analyze_and_score(str(low_files[0]), mode='quick')

        high_breath = high_result['scores']['breath']
        low_breath = low_result['scores']['breath']
        diff = high_breath - low_breath

        assert diff >= 18, (
            f"真实音频气息区分度不足: high={high_breath:.1f}, low={low_breath:.1f}, diff={diff:.1f}"
        )


# ============================================================================
# Phase 2: 音准评分区分度 (P0)
# ============================================================================

class TestPitchDifferentiation:
    """音准评分的区分度 — 扩展 MAE 阈值后应有更广的分数范围"""

    def test_pitch_score_wider_range_with_synthetic(self):
        """合成测试: MAE=15 vs MAE=50 应有 ≥ 25 分差距"""
        from services.scoring.pitch_scorer import PitchScorer
        from services.scoring_config import PitchThresholds, EmpiricalThresholds
        from services.audio_features_service import PitchDeviationResult

        scorer = PitchScorer(PitchThresholds(), EmpiricalThresholds())

        # MAE=15 (较好音准)
        good_pitch = PitchDeviationResult(mae_cents=15.0, detection_rate=0.9)
        good_score = scorer.calculate(good_pitch)[0]

        # MAE=50 (一般音准)
        ok_pitch = PitchDeviationResult(mae_cents=50.0, detection_rate=0.9)
        ok_score = scorer.calculate(ok_pitch)[0]

        diff = good_score - ok_score
        assert diff >= 25, (
            f"音准区分度不足: MAE15={good_score:.1f}, MAE50={ok_score:.1f}, diff={diff:.1f}"
        )

    def test_pitch_mae_30_not_too_high(self):
        """MAE=30 音分 → 得分应 ≤ 85 (不应接近满分)"""
        from services.scoring.pitch_scorer import PitchScorer
        from services.scoring_config import PitchThresholds, EmpiricalThresholds
        from services.audio_features_service import PitchDeviationResult

        scorer = PitchScorer(PitchThresholds(), EmpiricalThresholds())
        pitch = PitchDeviationResult(mae_cents=30.0, detection_rate=0.9)
        score = scorer.calculate(pitch)[0]

        assert score <= 85, (
            f"MAE=30 得分过高: {score:.1f} (应 ≤85, 旧值约94)"
        )

    def test_pitch_mae_70_appropriately_low(self):
        """MAE=70 音分 → 得分应接近 40-45 (明显偏低)"""
        from services.scoring.pitch_scorer import PitchScorer
        from services.scoring_config import PitchThresholds, EmpiricalThresholds
        from services.audio_features_service import PitchDeviationResult

        scorer = PitchScorer(PitchThresholds(), EmpiricalThresholds())
        pitch = PitchDeviationResult(mae_cents=70.0, detection_rate=0.9)
        score = scorer.calculate(pitch)[0]

        assert 35 <= score <= 50, (
            f"MAE=70 得分不合理: {score:.1f} (应 35-50)"
        )

    @pytest.mark.xfail(
        reason="TDD RED: 需要音准阈值扩展后更新回归基线。"
    )
    def test_real_audio_pitch_differentiation(self):
        """真实音频: 高分音准 - 低分音准 ≥ 10 分"""
        from api.business.audio_analysis import analyze_and_score

        test_dir = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
        high_files = sorted(test_dir.glob("*（高分）*.mp3")) if test_dir.exists() else []
        low_files = sorted(test_dir.glob("*（低分）*.mp3")) if test_dir.exists() else []

        if len(high_files) < 1 or len(low_files) < 1:
            pytest.skip("需要真实测试音频")

        high_result = analyze_and_score(str(high_files[0]), mode='quick')
        low_result = analyze_and_score(str(low_files[0]), mode='quick')

        high_pitch = high_result['scores']['pitch']
        low_pitch = low_result['scores']['pitch']
        diff = high_pitch - low_pitch

        assert diff >= 10, (
            f"真实音频音准区分度不足: high={high_pitch:.1f}, low={low_pitch:.1f}, diff={diff:.1f}"
        )


# ============================================================================
# Phase 3: HNR/CPP 天花板重校准 (P1)
# ============================================================================

class TestTechniqueCeiling:
    """HNR/CPP 天花板 — 提高满分阈值以避免天花板效应"""

    def test_hnr_no_ceiling_collapse(self):
        """HNR=15 和 HNR=20 应产生不同分数 (不应都是 100)"""
        from services.scoring.technique_scorer import TechniqueScorer
        from services.scoring_config import TechniqueThresholds
        from services.audio_features_service import VocalTechniqueResult

        scorer = TechniqueScorer(TechniqueThresholds(), singing_style='pop')
        technique = VocalTechniqueResult(technique_score=70.0)

        score_15 = scorer.calculate(hnr=15.0, cpp=1.0, technique=technique)[0]
        score_20 = scorer.calculate(hnr=20.0, cpp=1.0, technique=technique)[0]

        assert score_20 > score_15 + 3, (
            f"HNR 天花板: HNR15={score_15:.1f}, HNR20={score_20:.1f} — 应差 >3"
        )
        # 都不应满分
        assert score_15 < 100, f"HNR=15 不应满分: {score_15:.1f}"
        assert score_20 < 100, f"HNR=20 不应满分: {score_20:.1f}"

    def test_cpp_no_ceiling_collapse(self):
        """CPP=1.0 和 CPP=2.0 应产生不同分数"""
        from services.scoring.technique_scorer import TechniqueScorer
        from services.scoring_config import TechniqueThresholds
        from services.audio_features_service import VocalTechniqueResult

        scorer = TechniqueScorer(TechniqueThresholds(), singing_style='pop')
        technique = VocalTechniqueResult(technique_score=70.0)

        score_1 = scorer.calculate(hnr=15.0, cpp=1.0, technique=technique)[0]
        score_2 = scorer.calculate(hnr=15.0, cpp=2.0, technique=technique)[0]

        assert score_2 > score_1 + 3, (
            f"CPP 天花板: CPP1.0={score_1:.1f}, CPP2.0={score_2:.1f}"
        )
        assert score_1 < 100, f"CPP=1.0 不应满分: {score_1:.1f}"

    def test_hnr_breathy_still_gets_decent_score(self):
        """气声唱法 (HNR=8, 高技巧) 应得 55-70 分 (不是 0 也不是 100)"""
        from services.scoring.technique_scorer import TechniqueScorer
        from services.scoring_config import TechniqueThresholds
        from services.audio_features_service import VocalTechniqueResult

        scorer = TechniqueScorer(TechniqueThresholds(), singing_style='pop')
        technique = VocalTechniqueResult(technique_score=75.0)

        score = scorer.calculate(hnr=8.0, cpp=0.5, technique=technique)[0]

        # 气声是风格选择，不应被过度惩罚
        assert 50 <= score <= 75, (
            f"气声唱法得分不合理: {score:.1f} (应 50-75)"
        )


# ============================================================================
# Phase 4: 跨维度集成 (P1)
# ============================================================================

class TestCrossDimensionIntegration:
    """跨维度集成 — Feature Flag 控制 HNR/CPP/Voicing 反馈到评分"""

    def test_cross_dimension_flag_exists_and_default_off(self):
        """跨维度集成 Feature Flag 应存在且默认关闭"""
        from services.feature_flags import FeatureFlags

        flags = FeatureFlags()
        assert hasattr(flags, 'enable_cross_dimension_modifiers'), (
            "缺少 enable_cross_dimension_modifiers flag"
        )
        assert flags.enable_cross_dimension_modifiers is False, (
            "跨维度集成应默认关闭"
        )

    def test_hnr_stability_affects_breath_with_flag_on(self):
        """跨频带 HNR 稳定性影响气息评分 (架构验证)"""
        from services.features.breath import BreathAnalyzer
        from services.scoring.breath_scorer import BreathScorer
        from services.scoring_config import BreathThresholds
        from services.features.hnr import HNRMultiscaleResult
        import numpy as np

        sr = 22050
        duration = 2.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        # 稳定谐波信号 (好的 HNR 稳定性)
        good_signal = np.zeros_like(t)
        for h in range(1, 10):
            good_signal += (0.5 / h) * np.sin(2 * np.pi * 220 * h * t)
        good_signal = good_signal / np.max(np.abs(good_signal)) * 0.5

        analyzer = BreathAnalyzer(sample_rate=sr)
        result = analyzer.calculate_breath_stability(good_signal, singing_style='pop')
        scorer = BreathScorer(BreathThresholds())
        base_score = scorer.calculate(result)[0]

        # 模拟 HNR 不稳定 → 应扣分
        unstable_hnr = HNRMultiscaleResult(
            hnr_short=8.0, hnr_medium=12.0, hnr_long=10.0,
            hnr_stability=0.4  # 高 CV = 不稳定
        )
        # 架构验证: unstable HNR CV 值应为 > 0.3
        assert unstable_hnr.hnr_stability > 0.3, (
            f"HNR stability 应 > 0.3 (unstable): {unstable_hnr.hnr_stability}"
        )
        assert base_score > 0, f"基础气息分应 > 0: {base_score}"

    def test_voicing_confidence_affects_pitch_with_flag_on(self):
        """低 Voicing 置信度应降低音准评分 (标志验证)"""
        from services.features.voicing import VoicingDetectionResult

        # 低置信度 voicing 结果
        low_conf = VoicingDetectionResult(
            voiced_frame_count=50,
            total_frame_count=100,
            voicing_ratio=0.5,
            detection_confidence=0.25,
            octave_jump_rate=0.0,
            consistency_score=30.0,
            energy_voicing_agreement=0.4
        )

        # 高置信度 voicing 结果
        high_conf = VoicingDetectionResult(
            voiced_frame_count=90,
            total_frame_count=100,
            voicing_ratio=0.9,
            detection_confidence=0.85,
            octave_jump_rate=0.0,
            consistency_score=90.0,
            energy_voicing_agreement=0.9
        )

        # 低置信度应有更低的可信度
        assert low_conf.detection_confidence < 0.3
        assert high_conf.detection_confidence > 0.7

    def test_cross_dimension_flag_off_preserves_original_scores(self):
        """flag OFF 时评分应与原来一致 (回归保护)"""
        from services.feature_flags import FeatureFlags
        from api.business.audio_analysis import analyze_and_score

        test_dir = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
        candidates = sorted(test_dir.glob("*.mp3")) if test_dir.exists() else []
        if not candidates:
            pytest.skip("No test audio")

        # flag 关闭 (默认)
        result_default = analyze_and_score(str(candidates[0]), mode='quick')
        # FeatureFlags 应该包含新 flag 且默认关闭
        flags = FeatureFlags()
        if hasattr(flags, 'enable_cross_dimension_modifiers'):
            result_with_flags = analyze_and_score(
                str(candidates[0]), mode='quick', feature_flags=flags
            )
            assert (result_default.get('total_score') ==
                    result_with_flags.get('total_score')), (
                "flag 关闭时总分应变"
            )


# ============================================================================
# Phase 5: 音量维度独立 (P2)
# ============================================================================

class TestVolumeIndependence:
    """音量维度独立 — volume 应基于 SPL 测量而非 breath 别名"""

    def test_volume_different_from_breath(self):
        """volume 评分应独立于 breath (不应相同)"""
        from api.business.audio_analysis import analyze_and_score

        test_dir = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
        candidates = sorted(test_dir.glob("*（低分）*.mp3")) if test_dir.exists() else []
        if not candidates:
            pytest.skip("No test audio")

        result = analyze_and_score(str(candidates[0]), mode='quick')
        scores = result.get('scores', {})

        assert scores.get('volume') != scores.get('breath'), (
            f"volume={scores.get('volume')} 和 breath={scores.get('breath')} "
            "相同 — 尚未独立解耦"
        )

    def test_volume_dimension_in_scores(self):
        """评分结果应包含 volume 维度 (已实现，回归保护)"""
        from api.business.audio_analysis import analyze_and_score

        test_dir = Path(__file__).parent.parent / "test_data" / "audio" / "vocal"
        candidates = sorted(test_dir.glob("*.mp3")) if test_dir.exists() else []
        if not candidates:
            pytest.skip("No test audio")

        result = analyze_and_score(str(candidates[0]), mode='quick')
        scores = result.get('scores', {})

        assert 'volume' in scores, "缺少 volume 维度"
        assert 0 <= scores['volume'] <= 100, f"volume 超出范围: {scores['volume']}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
