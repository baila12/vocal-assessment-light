"""WebSocket 实时评分集成测试 — 8 tests"""

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
    """构造 4字节大端长度前缀 + Float32 PCM"""
    data = pcm.astype(np.float32).tobytes()
    prefix = struct.pack(">I", len(data))
    return prefix + data


def _generate_sine(duration_s: float, sr: int = 16000, freq: float = 440.0) -> np.ndarray:
    """生成正弦波测试音频"""
    t = np.linspace(0, duration_s, int(sr * duration_s), endpoint=False)
    return (np.sin(2 * np.pi * freq * t) * 0.5).astype(np.float32)


class TestWebSocketConnection:
    """WebSocket 连接生命周期测试"""

    def test_ws_handshake(self, client):
        """握手成功，收到 ready 事件"""
        with client.websocket_connect("/ws/v1/score") as ws:
            data = ws.receive_json()
            assert data["event"] == "ready"
            assert "session_id" in data
            assert len(data["session_id"]) == 12

    def test_ws_endpoint_sends_error_on_handler_exception(self, client, monkeypatch):
        """handle() 异常时外层兜底发 error 帧再关闭 (防客户端挂起, v7.14 审查 C1/E1).

        Starlette 全局 HTTP exception handler 不覆盖 WebSocket 路由,
        端点层需自带 try/except 安全网。
        """
        from backend.interfaces import ws as ws_module

        async def _boom(ws):
            await ws.accept()
            raise RuntimeError("handler failure")

        monkeypatch.setattr(ws_module._score_handler, "handle", _boom)

        with client.websocket_connect("/ws/v1/score") as ws:
            data = ws.receive_json()
            assert data["event"] == "error"
            assert "message" in data

    def test_ws_disconnect_cleanup(self, client):
        """正常断开时 session 被清理"""
        with client.websocket_connect("/ws/v1/score") as ws:
            data = ws.receive_json()
            session_id = data["session_id"]
            ws.close()
        # 验证 handler 不再持有该 session
        from backend.interfaces.ws import _score_handler
        assert session_id not in _score_handler._sessions


class TestProtocolFraming:
    """ADR-7: 4字节长度前缀协议测试"""

    def test_single_frame_parsing(self, client):
        """单个 PCM 帧被正确解析"""
        pcm = _generate_sine(0.2)  # 0.2s = 3200 samples
        frame = _make_pcm_frame(pcm)

        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready
            ws.send_bytes(frame)

            # 发送 stop 获取最终评分
            ws.send_text(json.dumps({"type": "stop"}))
            response = ws.receive_json()
            # 可能是 final_score 或 error (取决于音频时长)
            assert response["event"] in ("final_score", "error")

    def test_multiple_frames_combined(self, client):
        """ADR-7: 多个帧被 TCP 合并时正确分帧"""
        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready

            # 创建4个独立的帧
            chunks = []
            for _ in range(4):
                pcm = _generate_sine(0.15)  # 2400 samples each
                chunks.append(_make_pcm_frame(pcm))

            # 模拟 TCP 粘包: 发送2+2合并
            combined1 = chunks[0] + chunks[1]
            combined2 = chunks[2] + chunks[3]

            ws.send_bytes(combined1)
            ws.send_bytes(combined2)

            # 应该能正常工作 (不崩溃即正确分帧)
            ws.send_text(json.dumps({"type": "stop"}))
            response = ws.receive_json()
            assert response["event"] in ("final_score", "error")

    def test_length_prefix_integrity(self, client):
        """验证长度前缀字节序 (big-endian uint32)"""
        test_len = 8192  # 2048 samples * 4 bytes
        prefix = struct.pack(">I", test_len)
        decoded = struct.unpack(">I", prefix)[0]
        assert decoded == test_len, "big-endian uint32 编码/解码不一致"


class TestControlMessages:
    """JSON 控制帧测试"""

    def test_start_stop_flow(self, client):
        """start → stop → final_score 完整流程"""
        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready

            # 发送 start
            ws.send_text(json.dumps({"type": "start", "mode": "quick"}))
            # start 没有直接响应 (仅日志)

            # 发送足够的音频 (>1s for a valid score)
            pcm = _generate_sine(1.5, sr=16000)  # 1.5s of 440Hz
            frame = _make_pcm_frame(pcm)
            ws.send_bytes(frame)

            # 发送 stop
            ws.send_text(json.dumps({"type": "stop"}))
            response = ws.receive_json()
            assert response["event"] == "final_score"
            assert "total" in response
            assert "scores" in response
            assert 0 <= response["total"] <= 100

    def test_final_score_total_matches_weighted_dimensions(self, client):
        """总分量纲正确 — 与六维加权和一致 (防 /100.0 100x 缩小回归).

        v7.14 审查 C1: _score_lightweight 曾对已归一化权重和额外除 100,
        总分落在 0-1 区间 (如 0.67), 用户看到的分数全被判定为"待提升"。
        本测试断言总分 ≥10 (正常评分区间) 且与六维加权一致。
        """
        from backend.domain.assessment.scoring_weights import ScoringWeights

        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready
            ws.send_text(json.dumps({"type": "start", "mode": "quick"}))

            pcm = _generate_sine(1.5, sr=16000)
            ws.send_bytes(_make_pcm_frame(pcm))
            ws.send_text(json.dumps({"type": "stop"}))

            response = ws.receive_json()
            assert response["event"] == "final_score"
            assert "scores" in response

            # 关键量纲断言: 总分不应落在 0-1 区间 (100x 缩小 bug 特征)
            assert response["total"] >= 10, \
                f"总分量纲错误: {response['total']} 不应落在 0-1 区间"

            # 与六维加权和一致 (ScoringWeights 单一来源)
            scores = response["scores"]
            w = ScoringWeights.default()
            expected = (
                scores["pitch"] * w.pitch
                + scores["rhythm"] * w.rhythm
                + scores["breath"] * w.breath
                + scores["technique"] * w.technique
                + scores["muscle_strength"] * w.muscle
                + scores["artistry"] * w.artistry
            )
            assert abs(response["total"] - expected) < 0.5, \
                f"总分 {response['total']} 与加权和 {expected} 不一致"

    def test_final_score_surfaces_scoring_warnings_on_fallback(self, client, monkeypatch):
        """音高提取失败 → final_score 带 scoring_warnings (P1-5 M2: 假 50.0 可辨识)"""
        import librosa

        def _boom(*args, **kwargs):
            raise RuntimeError("pyin failure")

        monkeypatch.setattr(librosa, "pyin", _boom)

        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready
            ws.send_text(json.dumps({"type": "start", "mode": "quick"}))
            pcm = _generate_sine(1.5, sr=16000)
            ws.send_bytes(_make_pcm_frame(pcm))
            ws.send_text(json.dumps({"type": "stop"}))

            response = ws.receive_json()
            assert response["event"] == "final_score"
            assert "scoring_warnings" in response, "final_score 应透出 scoring_warnings"
            assert any("音准" in w for w in response["scoring_warnings"])

    def test_invalid_json_handled(self, client):
        """非法 JSON 返回 error 事件"""
        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready
            # 发送非法 JSON (通过 text 通道)
            ws.send_text("{not valid json")

            response = ws.receive_json()
            assert response["event"] == "error"

    def test_unknown_message_type(self, client):
        """未知消息类型返回 error"""
        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready
            ws.send_text(json.dumps({"type": "unknown_command"}))

            response = ws.receive_json()
            assert response["event"] == "error"


class TestStartWithSongId:
    """v7.12: start 消息携带 song_id → 会话存储 (选歌录音)"""

    def test_start_with_song_id_stores_on_session(self, client):
        """start 消息带 song_id → session.song_id 保存.

        stop 触发响应 (无音频 → error '录音时间过短'), 同步等待服务端处理。
        """
        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready
            ws.send_text(json.dumps(
                {"type": "start", "song_id": "moon_love", "mode": "quick"}
            ))
            ws.send_text(json.dumps({"type": "stop"}))
            response = ws.receive_json()  # error: 录音时间过短
            assert response["event"] == "error"

            from backend.interfaces.ws import _score_handler
            sessions = list(_score_handler._sessions.values())
            matched = [s for s in sessions if getattr(s, 'song_id', None) == 'moon_love']
            assert matched, '未找到携带 song_id 的会话'

    def test_start_without_song_id_keeps_none(self, client):
        """不带 song_id → session.song_id 保持 None"""
        with client.websocket_connect("/ws/v1/score") as ws:
            ws.receive_json()  # ready
            ws.send_text(json.dumps({"type": "start", "mode": "quick"}))
            ws.send_text(json.dumps({"type": "stop"}))
            response = ws.receive_json()
            assert response["event"] == "error"

            from backend.interfaces.ws import _score_handler
            sessions = list(_score_handler._sessions.values())
            assert any(getattr(s, 'song_id', None) is None for s in sessions)
