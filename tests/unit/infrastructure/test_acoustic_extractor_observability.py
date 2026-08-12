"""
AcousticFeatureExtractor 可观测性 TDD 测试 — v7.15 M3 修复轮

DEEP_REVIEW M3 (CONFIRMED): acoustic_feature_extractor.py 多个方法静默吞
librosa/numpy 异常, 返回 0/None/负值而不记录日志 → 生产无法观测特征提取失败。

修复原则 (TDD RED→GREEN):
  1. 保持优雅降级 — 提取器永不崩溃评分管线 (高稳定性)
  2. 失败必须可观测 — 每个静默 except Exception 升级为 logger.warning(exc_info=True)
  3. 现有 ImportError 回落分支 (librosa fallback / parselmouth 禁用) 属有意设计, 不改

测试策略: monkeypatch 子操作抛异常 → 断言 降级返回值 + WARNING 日志记录。
"""
from __future__ import annotations
import logging

import pytest
import numpy as np

from backend.domain.audio.acoustic_feature_extractor import (
    LibrosaAcousticExtractor,
)

HOP = 512


def _signal(sr: int = 22050, seconds: float = 1.0) -> np.ndarray:
    """合成 220Hz 正弦信号 (非静音, 可触发正常计算路径)"""
    t = np.linspace(0, seconds, int(sr * seconds), endpoint=False)
    return (np.sin(2 * np.pi * 220 * t) * 0.5).astype(np.float32)


def _fail(*args, **kwargs):
    raise RuntimeError("boom: injected failure")


class TestObservabilityOnFailure:
    """静默失败必须升级为 WARNING 日志 (M3 修复目标)"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.extractor = LibrosaAcousticExtractor()
        self.y = _signal()

    def test_hnr_failure_logs_warning(self, caplog):
        """HNR 计算失败 → 返回 0.0 + WARNING 日志 (而非静默/DEBUG)"""
        import librosa
        monkey = pytest.MonkeyPatch()
        monkey.setattr(librosa.effects, "hpss", _fail)
        try:
            with caplog.at_level(logging.WARNING, logger="backend.domain.audio.acoustic_feature_extractor"):
                result = self.extractor._compute_hnr(self.y, hpss_harmonic=None)
            assert result == 0.0, "HNR 应优雅降级为 0.0"
            assert any(
                "HNR" in r.message and r.levelno == logging.WARNING
                for r in caplog.records
            ), "HNR 失败应记录 WARNING 日志"
        finally:
            monkey.undo()

    def test_cpp_failure_logs_warning(self, caplog):
        """CPP 计算失败 → 返回 0.0 + WARNING 日志"""
        import librosa
        monkey = pytest.MonkeyPatch()
        monkey.setattr(librosa.util, "frame", _fail)
        try:
            with caplog.at_level(logging.WARNING, logger="backend.domain.audio.acoustic_feature_extractor"):
                result = self.extractor._compute_cpp(self.y)
            assert result == 0.0
            assert any(
                "CPP" in r.message and r.levelno == logging.WARNING
                for r in caplog.records
            ), "CPP 失败应记录 WARNING 日志"
        finally:
            monkey.undo()

    def test_spectral_tilt_failure_logs_warning(self, caplog):
        """Spectral tilt 计算失败 → 返回 -10.0 + WARNING 日志 (而非静默)"""
        monkey = pytest.MonkeyPatch()
        monkey.setattr(np.fft, "rfft", _fail)
        try:
            with caplog.at_level(logging.WARNING, logger="backend.domain.audio.acoustic_feature_extractor"):
                result = self.extractor._compute_spectral_tilt(self.y, 22050)
            assert result == -10.0
            assert any(
                "tilt" in r.message.lower() and r.levelno == logging.WARNING
                for r in caplog.records
            ), "Spectral tilt 失败应记录 WARNING 日志"
        finally:
            monkey.undo()

    def test_voicing_generic_failure_logs_warning(self, caplog):
        """Voicing 泛型异常 (非 ImportError) → 返回 (0.0, 0.0) + WARNING 日志"""
        import librosa
        monkey = pytest.MonkeyPatch()
        monkey.setattr(librosa, "pyin", _fail)
        try:
            with caplog.at_level(logging.WARNING, logger="backend.domain.audio.acoustic_feature_extractor"):
                result = self.extractor._compute_voicing(self.y, 22050)
            assert result == (0.0, 0.0)
            assert any(
                "voicing" in r.message.lower() and r.levelno == logging.WARNING
                for r in caplog.records
            ), "Voicing 泛型失败应记录 WARNING 日志"
        finally:
            monkey.undo()

    def test_mixed_audio_failure_logs_warning(self, caplog):
        """Mixed audio 检测失败 → 返回 (False, 0.0) + WARNING 日志 (而非静默)"""
        monkey = pytest.MonkeyPatch()
        monkey.setattr(np.fft, "rfft", _fail)
        try:
            with caplog.at_level(logging.WARNING, logger="backend.domain.audio.acoustic_feature_extractor"):
                result = self.extractor._detect_mixed_audio(self.y, 22050, hpss_ratio=0.5)
            assert result == (False, 0.0)
            assert any(
                "mixed" in r.message.lower() and r.levelno == logging.WARNING
                for r in caplog.records
            ), "Mixed audio 失败应记录 WARNING 日志"
        finally:
            monkey.undo()

    def test_extract_graceful_degrades_when_subcall_fails(self, caplog):
        """子操作失败 → extract() 仍返回 AcousticFeatures, 不崩溃 (高稳定性)"""
        import librosa
        monkey = pytest.MonkeyPatch()
        monkey.setattr(librosa.effects, "hpss", _fail)
        try:
            with caplog.at_level(logging.WARNING, logger="backend.domain.audio.acoustic_feature_extractor"):
                result = self.extractor.extract(self.y, 22050)
            from backend.domain.audio.feature_types import AcousticFeatures
            assert isinstance(result, AcousticFeatures)
            assert result.hnr >= 0.0
            assert result.cpp >= 0.0
        finally:
            monkey.undo()

    def test_import_error_fallback_still_works(self):
        """回归: librosa 缺失的 ImportError 回落路径必须保留 (有意设计, 非吞异常)"""
        import librosa
        monkey = pytest.MonkeyPatch()
        real_pyin = librosa.pyin
        monkey.setattr(librosa, "pyin", _fail)
        try:
            # 注入 ImportError 走能量+ZCR 回落
            def _raise_importerror(*a, **k):
                raise ImportError("no librosa")
            monkey.setattr(librosa, "pyin", _raise_importerror)
            ratio, conf = self.extractor._compute_voicing(self.y, 22050)
            assert 0.0 <= ratio <= 1.0
            assert 0.0 <= conf <= 1.0
        finally:
            monkey.setattr(librosa, "pyin", real_pyin)
            monkey.undo()
