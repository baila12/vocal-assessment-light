"""WebSocket 实时音高推送测试 — v7.13 pitch_update 接线

每 2s 新音频段 → 后端 PYIN → 发送 WsServerPitchUpdate。
独立进程运行 (与 test_ws_score.py 相同约定)。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + "/../..")

import struct
import json
import numpy as np
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from backend.main import create_app
    app = create_app()
    with TestClient(app) as c:
        yield c


def _make_pcm_frame(pcm: np.ndarray) -> bytes:
    data = pcm.astype(np.float32).tobytes()
    prefix = struct.pack(">I", len(data))
    return prefix + data


def _generate_sine(duration_s: float, sr: int = 16000, freq: float = 440.0) -> np.ndarray:
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * 0.5).astype(np.float32)


def _read_pitch_update(ws, attempts: int = 10) -> dict:
    """接收事件直到拿到 pitch_update"""
    for _ in range(attempts):
        msg = ws.receive_json()
        if msg.get("event") == "pitch_update":
            return msg
    pytest.fail("未收到 pitch_update 事件")


class TestWsPitchUpdate:
    """WebSocket 实时音高推送 — v7.13"""

    def test_pitch_update_received_after_2s_audio(self, client):
        """发送 ≥2s 音频 → 收到 pitch_update (frequencies/times/confidence)"""
        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready
            ws.send_text(json.dumps({"type": "start"}))
            ws.send_bytes(_make_pcm_frame(_generate_sine(2.2)))

            msg = _read_pitch_update(ws)
            assert len(msg["frequencies"]) > 0
            assert len(msg["times"]) == len(msg["frequencies"])
            assert len(msg["confidence"]) == len(msg["frequencies"])
            assert msg["duration"] > 0
            # 正弦波 → 存在非零频率
            assert any(f > 0 for f in msg["frequencies"])

    def test_pitch_update_no_song_id_still_sent(self, client):
        """未带 song_id 的 start 也应推送音高 (录音通用)"""
        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready
            ws.send_text(json.dumps({"type": "start"}))
            ws.send_bytes(_make_pcm_frame(_generate_sine(2.2)))

            msg = _read_pitch_update(ws)
            assert msg["event"] == "pitch_update"

    def test_pitch_update_times_advance_incrementally(self, client):
        """连续音频段 → 时间轴递增 (第二段时间从 ~2.2s 起)"""
        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready
            ws.send_text(json.dumps({"type": "start"}))
            ws.send_bytes(_make_pcm_frame(_generate_sine(2.2)))
            first = _read_pitch_update(ws)

            ws.send_bytes(_make_pcm_frame(_generate_sine(2.2)))
            second = _read_pitch_update(ws)

            assert first["times"][-1] <= 2.4
            assert second["times"][0] >= 1.8, \
                f"第二段时间应从 ~2.2s 起, 实际 {second['times'][0]:.2f}"

    def test_short_audio_no_premature_pitch_update(self, client):
        """<2s 音频 → 不应触发 pitch_update (样本阈值门控)"""
        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready
            ws.send_text(json.dumps({"type": "start"}))
            ws.send_bytes(_make_pcm_frame(_generate_sine(1.0)))

            # 发送 stop 并读取响应; 期间不应有 pitch_update
            ws.send_text(json.dumps({"type": "stop"}))
            while True:
                msg = ws.receive_json()
                if msg.get("event") == "pitch_update":
                    pytest.fail("1s 音频不应触发 pitch_update")
                if msg.get("event") == "final_score" or msg.get("event") == "error":
                    break
