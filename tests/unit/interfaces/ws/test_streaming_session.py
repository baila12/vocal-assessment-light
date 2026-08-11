"""
StreamingSession.compute_partial 单元测试 — P0-3 (审查 5.2 低音歧视 + 假节奏)

修复:
- 节奏无参考不可评 → None, 而非硬编码 50.0 假分 (前端 ?? 0 安全)
- 音准公式去绝对频率偏置 (261.6Hz C4 基准歧视男低音) → 改为 voiced 覆盖率
"""

import numpy as np

from backend.interfaces.ws.streaming_session import StreamingSession


def _sine(duration_s: float, sr: int = 16000, freq: float = 440.0) -> np.ndarray:
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * 0.5).astype(np.float32)


class TestPartialRhythm:
    """假节奏修复 — rhythm 应为 None 而非 50.0"""

    def test_rhythm_is_none_not_fake_50(self):
        """无参考歌曲 → 节奏不可评 → None (不再硬编码 50.0)"""
        session = StreamingSession()
        session.append_audio(_sine(3.0))
        partial = session.compute_partial()
        assert partial["rhythm"] is None, \
            f"节奏无参考不可评, 应为 None, 实际 {partial['rhythm']}"

    def test_short_buffer_rhythm_none(self):
        """不足 1s 的短缓冲 → rhythm 也应为 None"""
        session = StreamingSession()
        session.append_audio(_sine(0.5))
        partial = session.compute_partial()
        assert partial["rhythm"] is None

    def test_partial_event_and_progress(self):
        """partial_score 事件结构与进度字段不变"""
        session = StreamingSession()
        session.append_audio(_sine(3.0))
        partial = session.compute_partial()
        assert partial["event"] == "partial_score"
        assert "pitch" in partial
        assert "progress" in partial
        assert "elapsed_s" in partial


class TestPartialPitch:
    """中性音准公式 — 低音歌手不因绝对频率被歧视"""

    @staticmethod
    def _monkeypyin(monkeypatch, freq: float, voiced_ratio: float = 1.0):
        import librosa
        n_frames = 16000 * 3 // 512
        f0 = np.full(n_frames, float(freq), dtype=np.float64)
        if voiced_ratio < 1.0:
            f0[int(n_frames * voiced_ratio):] = np.nan
        voiced = (~np.isnan(f0)).astype(bool)
        monkeypatch.setattr(librosa, "pyin", lambda *a, **k: (f0, voiced, None))

    def test_low_frequency_singer_not_penalized(self, monkeypatch):
        """男低音 (C2=65Hz) 唱得稳定 → 音准分不被 261.6 基准压到 0"""
        self._monkeypyin(monkeypatch, freq=65.0, voiced_ratio=1.0)
        session = StreamingSession()
        session.append_audio(_sine(3.0, freq=65.0))
        partial = session.compute_partial()
        assert partial["pitch"] >= 50, \
            f"低音稳定歌唱音准分应 ≥50 (中性公式), 实际 {partial['pitch']}"

    def test_high_frequency_singer_consistent(self, monkeypatch):
        """高音歌手 (C6=1046Hz) 与低音同规则 — 不为绝对频率虚高"""
        self._monkeypyin(monkeypatch, freq=1046.0, voiced_ratio=1.0)
        session = StreamingSession()
        session.append_audio(_sine(3.0, freq=1046.0))
        partial = session.compute_partial()
        assert 0 <= partial["pitch"] <= 100

    def test_no_voice_returns_zero(self, monkeypatch):
        """无声 → 音准 0"""
        self._monkeypyin(monkeypatch, freq=440.0, voiced_ratio=0.0)
        session = StreamingSession()
        session.append_audio(_sine(3.0))
        partial = session.compute_partial()
        assert partial["pitch"] == 0.0

    def test_partial_voiced_coverage_metric(self, monkeypatch):
        """音准分反映 voiced 覆盖率 (中性、可解释) — 覆盖率越高分越高"""
        self._monkeypyin(monkeypatch, freq=440.0, voiced_ratio=0.5)
        session = StreamingSession()
        session.append_audio(_sine(3.0))
        partial_half = session.compute_partial()

        self._monkeypyin(monkeypatch, freq=440.0, voiced_ratio=1.0)
        session2 = StreamingSession()
        session2.append_audio(_sine(3.0))
        partial_full = session2.compute_partial()

        assert partial_full["pitch"] > partial_half["pitch"]
