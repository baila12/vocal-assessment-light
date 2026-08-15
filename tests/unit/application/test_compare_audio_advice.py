"""CompareAudioUseCase 建议复用 AdviceGenerator — v7.19 E5

目标: 对比分析的建议不再由 domain 层 generate_suggestions 硬编码,
而是复用 DDD application 层 AdviceGenerator (消除诊断/建议硬编码)。

策略: mock ComparisonService (返回偏差 dict) → 验证 execute_lightweight 输出
suggestions 走 AdviceGenerator (含维度建议/表扬模板), 且八度/速度诊断保留。
"""
import pytest


class TestCompareAudioSuggestions:
    """execute_lightweight 建议复用 AdviceGenerator"""

    def _make_result(self, **dev_overrides):
        """构造真实 ComparisonResult (AlignmentData + DeviationData + DDD 评分)"""
        from backend.application.comparison.compare_audio import CompareAudioUseCase
        from backend.domain.comparison.entities import (
            ComparisonResult, AlignmentData, DeviationData,
        )
        # rhythm avg_deviation=250ms → 节奏 60 分 (最弱) — 触发 '节奏建议'
        # octave_error_rate/tempo_ratio 经 dev_overrides 覆盖 (默认 0.0/1.0)
        defaults = dict(octave_error_rate=0.0, tempo_ratio=1.0)
        defaults.update(dev_overrides)
        dev = DeviationData(
            avg_pitch_cents=15.0, max_pitch_cents=40.0,
            avg_rhythm_ms=250.0, avg_volume_percent=0.2,
            avg_breath_stability=0.8,
            **defaults,
        )
        scoring = CompareAudioUseCase()._scoring.score(dev, confidence=0.9)
        return ComparisonResult(
            alignment=AlignmentData(confidence=0.9),
            deviation=dev,
            scoring=scoring,
        )

    def _run(self, monkeypatch, **dev_overrides):
        from backend.application.comparison.compare_audio import CompareAudioUseCase
        result = self._make_result(**dev_overrides)
        monkeypatch.setattr(CompareAudioUseCase, 'execute',
                            lambda self, std, user, style='pop': result)
        return CompareAudioUseCase().execute_lightweight('std.wav', 'user.wav')

    def test_suggestions_generated_by_advice_generator(self, monkeypatch):
        """suggestions 应含 AdviceGenerator 维度建议模板 (如 '音准建议'/'气息建议')"""
        dto = self._run(monkeypatch)
        assert dto['suggestions'], '应有建议'
        # 节奏 avg_deviation=250ms → 节奏 60 分 → 最弱维度 → '节奏建议'
        assert any('节奏建议' in s for s in dto['suggestions']), (
            f"应复用 AdviceGenerator 生成节奏建议, 实际 {dto['suggestions']}"
        )

    def test_suggestions_no_legacy_format(self, monkeypatch):
        """suggestions 不应再是 legacy generate_suggestions 的旧文案格式
        (旧格式含 '跟着节拍器练习' 无 '建议：' 模板前缀)
        """
        dto = self._run(monkeypatch)
        for s in dto['suggestions']:
            assert not s.startswith('节奏偏差明显'), (
                f"不应再是 legacy 硬编码文案, 实际 {s}"
            )

    def test_octave_and_tempo_diagnosis_retained(self, monkeypatch):
        """v7.18 P1 信号 (八度/速度) 诊断仍保留 — 对比特有, AdviceGenerator 不覆盖"""
        dto = self._run(monkeypatch, octave_error_rate=0.5, tempo_ratio=1.15)
        assert any('跨八度' in d for d in dto['diagnosis']), (
            f"八度诊断应保留, 实际 {dto['diagnosis']}"
        )
        assert any('快' in d for d in dto['diagnosis']), (
            f"速度诊断应保留, 实际 {dto['diagnosis']}"
        )

    def test_diagnosis_retained(self, monkeypatch):
        """普通维度诊断 (音准/节奏/音量) 仍保留"""
        dto = self._run(monkeypatch)
        assert any('音准' in d for d in dto['diagnosis']), (
            f"音准诊断应保留, 实际 {dto['diagnosis']}"
        )
        assert any('节奏' in d for d in dto['diagnosis']), (
            f"节奏诊断应保留, 实际 {dto['diagnosis']}"
        )


class TestCompareAudioMaxPitchMapping:
    """v7.19 整理回归: execute() 应把 legacy max_deviation 映射进 DeviationData.

    旧 bug: execute() 构造 DeviationData 时只取 avg_deviation, 遗漏 max_deviation
    → _score_pitch 的 max_deviation 恒 0.0 / problem_count 恒 0 (诊断失真)。
    回归测试 mock ComparisonService.compare_audio_files, 走真实 execute() 映射路径。
    """

    def _legacy_result(self):
        return {
            "success": True,
            "confidence": 0.9,
            "method": "three_level_dtw",
            "compute_time_ms": 10,
            "avg_cents_error": 30.0,
            "octave_error_rate": 0.0,
            "tempo_ratio": 1.0,
            "dimensions": {
                "pitch": {"avg_deviation": 30.0, "max_deviation": 150.0},
                "rhythm": {"avg_deviation": 40.0},
                "volume": {"avg_deviation": 0.2},
                "breath": {"stability": 0.8},
            },
        }

    def test_max_pitch_cents_mapped_from_legacy(self, monkeypatch):
        from backend.application.comparison.compare_audio import CompareAudioUseCase
        from services.comparison.comparison_service import ComparisonService

        legacy_result = self._legacy_result()
        monkeypatch.setattr(
            ComparisonService, "compare_audio_files",
            lambda _self, s, u, style="pop": legacy_result,
        )
        result = CompareAudioUseCase().execute("std.wav", "user.wav")

        assert result.deviation.max_pitch_cents == pytest.approx(150.0), (
            "legacy max_deviation 应映射进 DeviationData.max_pitch_cents (旧实现遗漏)"
        )
        assert result.scoring.pitch.max_deviation == pytest.approx(150.0), (
            "评分 pitch.max_deviation 应为 150 (旧实现恒 0)"
        )

    def test_avg_pitch_cents_still_mapped(self, monkeypatch):
        """avg_pitch_cents 原有映射不回归"""
        from backend.application.comparison.compare_audio import CompareAudioUseCase
        from services.comparison.comparison_service import ComparisonService

        legacy_result = self._legacy_result()
        monkeypatch.setattr(
            ComparisonService, "compare_audio_files",
            lambda _self, s, u, style="pop": legacy_result,
        )
        result = CompareAudioUseCase().execute("std.wav", "user.wav")
        assert result.deviation.avg_pitch_cents == pytest.approx(30.0)
