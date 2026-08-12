"""
AudioService.analyze 错误可观测性 TDD 测试 — v7.15 M4 修复轮

DEEP_REVIEW M4 (CONFIRMED): services/audio_service.py analyze() 整个分析块
包在 try/except 中, 失败仅返回 `error=str(e)` — 根因 (traceback) 被丢弃,
失败点无任何日志 → 生产无法诊断分析失败的真实原因。

修复原则 (TDD RED→GREEN):
  1. 保持契约 — 仍返回 success=False 的 AudioAnalysisResult (调用方依赖)
  2. 失败可观测 — 失败时 logger.exception() 记录完整 traceback (root cause)

测试策略: 写入真实正弦 wav (使 librosa.load + Path.stat 自然成功),
仅 patch 子操作抛异常 → 断言 降级结果 + ERROR 日志携带 traceback。
"""
from __future__ import annotations
import logging

import numpy as np
import pytest
import scipy.io.wavfile as wavfile

from services.audio_service import AudioService, AudioAnalysisResult

SR = 16000


def _write_sine_wav(path, seconds: float = 1.0):
    """写入 220Hz 1s 正弦 wav — 真实文件 I/O 路径 (librosa.load + Path.stat 成功)"""
    t = np.linspace(0, seconds, int(SR * seconds), endpoint=False)
    audio = (np.sin(2 * np.pi * 220 * t) * 0.5 * 32767).astype(np.int16)
    wavfile.write(str(path), SR, audio)
    return path


def _boom(self, _audio_data):
    """替换 _analyze_volume — 以类属性绑定调用 (self 自动传入)"""
    raise RuntimeError("injected analysis failure")


class TestAnalyzeErrorObservability:
    """analyze() 失败必须记录带 traceback 的 ERROR 日志 (M4 修复目标)"""

    def test_analyze_failure_logs_error_with_traceback(self, tmp_path, caplog, monkeypatch):
        """子操作失败 → success=False + ERROR 日志含 traceback (当前静默 → RED)"""
        service = AudioService()
        monkeypatch.setattr(AudioService, "_analyze_volume", _boom)

        wav_path = _write_sine_wav(tmp_path / "sample.wav")
        with caplog.at_level(logging.ERROR, logger="services.audio_service"):
            result = service.analyze(str(wav_path), quick_mode=True)

        # 契约保持: success=False 结果 + 根因消息
        assert isinstance(result, AudioAnalysisResult)
        assert result.success is False
        assert "injected analysis failure" in (result.error or "")

        # NEW (M4): 失败必须记录 ERROR 日志且携带 traceback (root cause)
        assert any(
            r.levelno == logging.ERROR and r.exc_info is not None
            for r in caplog.records
        ), "analyze() 失败应记录带 traceback 的 ERROR 日志"

    def test_analyze_failure_preserves_error_message(self, tmp_path, monkeypatch):
        """根因消息字符串必须透传到 result.error (既有契约, 回归保护)"""
        service = AudioService()
        monkeypatch.setattr(AudioService, "_analyze_volume", _boom)

        wav_path = _write_sine_wav(tmp_path / "x.wav")
        result = service.analyze(str(wav_path), quick_mode=True)
        assert result.success is False
        assert result.error == "injected analysis failure"

    def test_successful_analysis_does_not_log_error(self, tmp_path, caplog):
        """成功路径不得产生 ERROR 日志 (防过度日志)"""
        service = AudioService()
        wav_path = _write_sine_wav(tmp_path / "ok.wav")
        with caplog.at_level(logging.ERROR, logger="services.audio_service"):
            result = service.analyze(
                str(wav_path), quick_mode=True,
                include_waveform=True, include_pitch_curve=True,
            )
        assert result.success is True
        assert not any(r.levelno == logging.ERROR for r in caplog.records)
