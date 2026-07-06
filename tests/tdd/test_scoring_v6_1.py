"""
TDD 测试 — v6.1 评分区分度修复 (真实信号驱动)

测试范围:
  - Technique 基线: 50→0 (仅检测到的技巧加分)
  - Breath 连续评分: 步进加分→连续线性映射
  - Artistry 独立评分: 基于真实声学特征, 非其他维度加权

设计原则:
  - 分数从真实声学测量推导, 不凭空制造
  - 连续线性映射替代离散阈值
  - 所有子维度 0-100 范围
"""
import pytest
import numpy as np
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════════
# Technique 基线修复 (v6.1)
# ═══════════════════════════════════════════════════════════════════════════

class TestTechniqueBaselineFix:
    """Technique 评分: 移除 50 分地板, 仅检测到的技巧加分"""

    def test_zero_techniques_gets_zero_score(self):
        """零技巧检测 → technique_score = 0"""
        from services.features.technique import TechniqueAnalyzer

        analyzer = TechniqueAnalyzer(sample_rate=22050)
        sr = 22050
        t = np.linspace(0, 2, int(sr * 2), endpoint=False)
        signal = np.sin(2 * np.pi * 440 * t) * 0.5

        result = analyzer.detect_vocal_techniques(np.array([]), signal)
        assert result.technique_score == 0, \
            f"零技巧应得 0 分, 非 {result.technique_score}"

    def test_technique_score_range_zero_to_ninety(self):
        """有技巧检测时分数应在 0-95 范围"""
        from services.features.technique import TechniqueAnalyzer

        analyzer = TechniqueAnalyzer(sample_rate=22050)
        sr = 22050
        duration = 3.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)

        # 模拟颤音: f0 以 6Hz 波动 ±0.5 半音
        f0 = 440.0 * (2 ** (0.5 * np.sin(2 * np.pi * 6 * t) / 12))
        f0 = f0.astype(np.float64)
        phase = 2 * np.pi * np.cumsum(f0) / sr
        signal = np.sin(phase) * 0.5

        result = analyzer.detect_vocal_techniques(f0, signal)

        if result.vibrato_count > 0:
            assert result.technique_score > 0
            assert result.technique_score < 95, \
                f"单一颤音不应超 95, 实际: {result.technique_score}"
        else:
            pytest.skip("合成颤音未被检测到, 跳过基线验证")

    def test_real_audio_technique_range(self, cached_quick_result, cached_bad_result):
        """真音频 technique_score 0-100 范围"""
        if cached_quick_result is None:
            pytest.skip("No cached result")

        tech = cached_quick_result.get('scores', {}).get('technique', 0)
        assert 0 <= tech <= 100, f"Good singer technique {tech} out of range"

        if cached_bad_result:
            tech_bad = cached_bad_result.get('scores', {}).get('technique', 0)
            assert 0 <= tech_bad <= 100, f"Bad singer technique {tech_bad} out of range"


# ═══════════════════════════════════════════════════════════════════════════
# Breath 连续评分 (v6.1)
# ═══════════════════════════════════════════════════════════════════════════

class TestBreathContinuousScoring:
    """Breath 子维度: 步进加分→连续线性映射"""

    def test_breath_sub_score_is_continuous(self):
        """相似信号的分数差应 < 30 (连续而非离散跳变)"""
        from services.features.breath import BreathAnalyzer

        analyzer = BreathAnalyzer(sample_rate=22050)
        sr = 22050
        duration = 3.0
        t = np.linspace(0, duration, int(sr * duration), endpoint=False)
        signal = np.zeros_like(t)
        for h in range(1, 6):
            signal += (0.3 / h) * np.sin(2 * np.pi * 330 * h * t)
        signal = signal / np.max(np.abs(signal)) * 0.5

        f0 = np.full(50, 330.0)
        r1 = analyzer.calculate_breath_stability(signal, f0=f0)
        r2 = analyzer.calculate_breath_stability(signal * 0.7, f0=f0)

        diff = abs(r1.long_note_support_score - r2.long_note_support_score)
        assert diff < 30, f"相似信号分数差应 < 30, 实际: {diff:.1f}"

    def test_silence_gets_low_breath_score(self):
        """极低能量信号气息分 < 40"""
        from services.features.breath import BreathAnalyzer

        analyzer = BreathAnalyzer(sample_rate=22050)
        sr = 22050
        np.random.seed(42)
        noise = np.random.randn(int(sr * 2)) * 0.01

        result = analyzer.calculate_breath_stability(noise)
        assert result.professional_breath_score < 40, \
            f"极弱信号气息分应 < 40, 实际: {result.professional_breath_score:.1f}"

    def test_breath_score_bounded_zero_to_hundred(self):
        """所有子维度分数 0-100"""
        from services.features.breath import BreathAnalyzer

        analyzer = BreathAnalyzer(sample_rate=22050)
        sr = 22050
        t = np.linspace(0, 2, int(sr * 2), endpoint=False)
        signal = np.sin(2 * np.pi * 440 * t) * 0.5
        f0 = np.full(50, 440.0)

        result = analyzer.calculate_breath_stability(signal, f0=f0)
        scores = [
            result.long_note_support_score,
            result.dynamic_control_score,
            result.breath_design_score,
            result.breath_technique_score,
            result.professional_breath_score,
        ]
        for i, s in enumerate(scores):
            assert 0 <= s <= 100, f"子维度[{i}] = {s:.1f}, 超出 0-100"


# ═══════════════════════════════════════════════════════════════════════════
# Artistry 独立评分 (v6.1)
# ═══════════════════════════════════════════════════════════════════════════

class TestArtistryIndependentScoring:
    """Artistry: 基于真实声学特征独立评分, 非其他维度加权"""

    def test_artistry_not_pure_copy_of_other_scores(self, cached_quick_result):
        """艺术分不应完全等于加权平均"""
        if cached_quick_result is None:
            pytest.skip("No cached result")

        scores = cached_quick_result.get('scores', {})
        artistry = scores.get('artistry', 0)
        pitch = scores.get('pitch', 0)
        rhythm = scores.get('rhythm', 0)
        breath = scores.get('breath', 0)
        technique = scores.get('technique', 0)

        # 旧公式
        old_formula = pitch * 0.20 + rhythm * 0.25 + breath * 0.20 + technique * 0.35
        diff = abs(artistry - old_formula)

        # v6.1: 艺术分应显著不同于旧公式
        assert diff > 3, \
            f"Artistry ({artistry:.0f}) too close to weighted avg ({old_formula:.0f}), diff={diff:.1f}"

    def test_artistry_uses_acoustic_features(self):
        """ArtistryScorer 应使用独立声学特征方法"""
        from services.scoring.artistry_scorer import ArtistryScorer
        import inspect

        source = inspect.getsource(ArtistryScorer.calculate)
        acoustic_terms = ['vibrato', 'dynamic', 'phrase', 'pitch_variation']
        found = [t for t in acoustic_terms if t.lower() in source.lower()]
        assert len(found) >= 2, f"应使用声学特征, 找到: {found}"

    @pytest.mark.xfail(
        reason="TDD RED: ArtistryScorer 已重构为独立评分但尚未接受全部声学结果。"
               "已: vibrato_quality + dynamic_range + phrase_coherence"
    )
    def test_artistry_scorer_accepts_full_acoustic_result(self):
        """ArtistryScorer.calculate() 接受完整声学分析结果"""
        from services.scoring.artistry_scorer import ArtistryScorer
        import inspect

        sig = inspect.signature(ArtistryScorer.calculate)
        params = list(sig.parameters.keys())
        # v6.1 已接受 technique + breath + audio_data + f0 + emotions
        assert 'technique' in params and 'breath' in params, \
            f"应接受 technique 和 breath 参数, 当前: {params}"


# ═══════════════════════════════════════════════════════════════════════════
# 音量维度独立 (v5.19 GREEN)
# ═══════════════════════════════════════════════════════════════════════════

class TestVolumeDimension:
    """音量作为独立维度 — 基于 dynamic_range, 非 breath 衍生"""

    def test_volume_dimension_present_in_scores(self, cached_quick_result):
        """评分结果应包含独立的 volume 维度"""
        if cached_quick_result is None:
            pytest.skip("No cached result")

        scores = cached_quick_result.get('scores', {})
        assert 'volume' in scores, "缺少 volume 维度"
        assert 0 <= scores['volume'] <= 100

    def test_volume_independent_from_breath(self, cached_quick_result):
        """volume 评分应独立于 breath"""
        if cached_quick_result is None:
            pytest.skip("No cached result")

        scores = cached_quick_result.get('scores', {})
        assert scores.get('volume') != scores.get('breath'), \
            "volume 和 breath 分数相同 — 可能尚未独立解耦"
