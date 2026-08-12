"""
AudioDLHelpers 可观测性 TDD 测试 — v7.15 M5 修复轮

DEEP_REVIEW M5 (CONFIRMED): services/audio_dl_helpers.py 4 个 DL 辅助方法
`except Exception as e` 后 `logger.warning(f"...: {e}")` — 仅记录错误消息字符串,
不携带 traceback (无 exc_info) → 生产无法定位 DL 分析失败的真实堆栈。

修复原则 (TDD RED→GREEN):
  1. 保持优雅降级 — 失败仍返回 None (调用方已用 `if result:` 守卫, 契约安全)
  2. 失败可观测 — WARNING 日志升级为 exc_info=True, 保留完整 root cause traceback
"""
from __future__ import annotations
import logging

import pytest

from services.audio_dl_helpers import AudioDLHelpers

WARNING = logging.WARNING


def _fail(self, *args, **kwargs):
    raise RuntimeError("injected dl failure")


def _assert_warning_with_traceback(caplog, message_fragment: str):
    """断言存在带 traceback 的 WARNING 记录 (M5 修复目标)"""
    assert any(
        r.levelno == WARNING
        and message_fragment in r.getMessage()
        and r.exc_info is not None
        for r in caplog.records
    ), f"应记录含 traceback 的 WARNING: {message_fragment}"


class TestDlHelpersObservability:
    """DL 辅助方法失败必须记录带 traceback 的 WARNING (M5 修复目标)"""

    def test_voice_quality_failure_logs_warning_with_traceback(self, caplog, monkeypatch):
        """人声质量检测失败 → 返回 None + WARNING 含 traceback (当前仅 {e} 无 exc_info → RED)"""
        helper = AudioDLHelpers()
        monkeypatch.setattr(AudioDLHelpers, "_get_voice_quality_detector", _fail)
        with caplog.at_level(WARNING, logger="services.audio_dl_helpers"):
            result = helper.run_voice_quality_detection("x.wav")
        assert result is None
        _assert_warning_with_traceback(caplog, "Voice quality detection failed")

    def test_style_classification_failure_logs_warning_with_traceback(self, caplog, monkeypatch):
        """唱法识别失败 → 返回 None + WARNING 含 traceback"""
        helper = AudioDLHelpers()
        monkeypatch.setattr(AudioDLHelpers, "_get_style_classifier", _fail)
        with caplog.at_level(WARNING, logger="services.audio_dl_helpers"):
            result = helper.run_style_classification("x.wav")
        assert result is None
        _assert_warning_with_traceback(caplog, "Style classification failed")

    def test_dtw_failure_logs_warning_with_traceback(self, caplog, monkeypatch):
        """自参照 DTW 失败 → 返回 None + WARNING 含 traceback"""
        helper = AudioDLHelpers()
        monkeypatch.setattr(AudioDLHelpers, "_get_self_ref_dtw", _fail)
        with caplog.at_level(WARNING, logger="services.audio_dl_helpers"):
            result = helper.run_self_referenced_dtw("x.wav")
        assert result is None
        _assert_warning_with_traceback(caplog, "Self-referenced DTW failed")

    def test_music_style_failure_logs_warning_with_traceback(self, caplog, monkeypatch):
        """音乐风格分析失败 → 返回 None + WARNING 含 traceback"""
        helper = AudioDLHelpers()
        monkeypatch.setattr(AudioDLHelpers, "_get_style_analyzer", _fail)
        with caplog.at_level(WARNING, logger="services.audio_dl_helpers"):
            result = helper.run_music_style_analysis("x.wav")
        assert result is None
        _assert_warning_with_traceback(caplog, "Music style analysis failed")
