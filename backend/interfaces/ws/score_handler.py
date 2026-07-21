"""
ScoreWebSocketHandler — Phase 3 WebSocket 实时评分处理器

ADR-7: 4字节大端长度前缀防 TCP 粘包。
二进制帧: [4-byte uint32 BE length][Float32Array PCM data]
JSON 帧: {"type": "start"|"stop"}
"""

from __future__ import annotations
import struct
import json
import logging
from typing import Optional

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect

from backend.interfaces.ws.streaming_session import StreamingSession
from backend.interfaces.ws.schemas import (
    WsClientStart, WsClientStop,
    WsServerReady, WsServerPartialScore,
    WsServerQualityWarning, WsServerFinalScore, WsServerError,
)

logger = logging.getLogger(__name__)


class ScoreWebSocketHandler:
    """WebSocket 实时评分 — 管理连接生命周期和二进制流解析"""

    MAX_SESSIONS = 10  # 最大并发连接数

    def __init__(self) -> None:
        self._sessions: dict[str, StreamingSession] = {}

    def _create_session(self) -> StreamingSession:
        """创建新会话 — 超出上限时拒绝"""
        if len(self._sessions) >= self.MAX_SESSIONS:
            raise RuntimeError("服务器繁忙，请稍后重试")
        session = StreamingSession()
        self._sessions[session.id] = session
        return session

    def _remove_session(self, session_id: str) -> None:
        """移除会话并清理资源"""
        session = self._sessions.pop(session_id, None)
        if session:
            session.cleanup()

    async def handle(self, ws: WebSocket) -> None:
        """WebSocket 连接主循环"""
        await ws.accept()

        try:
            session = self._create_session()
        except RuntimeError as e:
            await ws.send_json({"event": "error", "message": str(e)})
            await ws.close(code=1013)
            return

        session.is_active = True
        await ws.send_json(WsServerReady(
            event="ready", session_id=session.id
        ).model_dump())

        buffer = bytearray()

        try:
            while True:
                msg = await ws.receive()

                msg_type = msg.get("type", "")
                if msg_type == "websocket.disconnect":
                    break

                if "text" in msg:
                    await self._handle_json(ws, session, msg["text"].encode("utf-8"))
                elif "bytes" in msg:
                    raw = msg["bytes"]
                    buffer.extend(raw)
                    await self._parse_frames(ws, session, buffer)

        except WebSocketDisconnect:
            logger.info(f"WS session {session.id} disconnected")
        except Exception as e:
            logger.exception(f"WS session {session.id} error: {e}")
            try:
                await ws.send_json(WsServerError(
                    event="error", message=str(e)
                ).model_dump())
            except Exception:
                pass
        finally:
            self._remove_session(session.id)

    async def _parse_frames(
        self, ws: WebSocket, session: StreamingSession, buffer: bytearray
    ) -> None:
        """
        ADR-7: 4字节长度前缀防粘包解析

        即使 TCP 合并多个帧为一个 WebSocket 消息，也能正确切分。
        """
        while len(buffer) >= 4:
            frame_len = struct.unpack(">I", buffer[:4])[0]  # big-endian uint32
            if len(buffer) < 4 + frame_len:
                break  # 帧不完整，等待更多数据

            pcm = np.frombuffer(
                buffer[4:4 + frame_len], dtype=np.float32
            ).copy()

            session.append_audio(pcm)
            del buffer[:4 + frame_len]

            # 每2秒推送增量评分
            if session.ready_for_partial():
                partial = session.compute_partial()
                await ws.send_json(partial)

    async def _handle_json(
        self, ws: WebSocket, session: StreamingSession, raw: bytes
    ) -> None:
        """处理 JSON 控制帧"""
        try:
            data = json.loads(raw.decode("utf-8"))
            msg_type = data.get("type", "")

            if msg_type == "start":
                req = WsClientStart(**data)
                session.mode = req.mode
                logger.info(f"WS session {session.id} started, mode={req.mode}")

            elif msg_type == "stop":
                req = WsClientStop(**data)
                await self._compute_final(ws, session)

            else:
                await ws.send_json(WsServerError(
                    event="error", message=f"未知的消息类型: {msg_type}"
                ).model_dump())

        except json.JSONDecodeError:
            await ws.send_json(WsServerError(
                event="error", message="无效的 JSON 格式"
            ).model_dump())
        except Exception as e:
            await ws.send_json(WsServerError(
                event="error", message=str(e)
            ).model_dump())

    async def _compute_final(self, ws: WebSocket, session: StreamingSession) -> None:
        """停止录音 → 计算最终六维评分"""
        buffer = session.audio_buffer
        if buffer is None or len(buffer) < session._sample_rate:  # < 1s
            await ws.send_json(WsServerError(
                event="error", message="录音时间过短 (<1s)"
            ).model_dump())
            return

        try:
            result = await self._score_lightweight(buffer, session)
            await ws.send_json(WsServerFinalScore(
                event="final_score",
                total=result.get("total_score", 0),
                scores=result.get("scores", {}),
                timbre_adjustment=result.get("timbre_adjustment", 0),
                level=result.get("level", ""),
                grade=result.get("grade", ""),
                advice=result.get("advice", []),
                duration_s=round(session.duration, 1),
            ).model_dump())

        except Exception as e:
            logger.exception(f"Final scoring error: {e}")
            await ws.send_json(WsServerError(
                event="error", message=f"评分失败: {e}"
            ).model_dump())

    async def _score_lightweight(self, buffer: np.ndarray, session: StreamingSession) -> dict:
        """轻量级评分: 仅 NumPy/librosa, 不加载 DL 模型 (<1s 延迟)"""
        import librosa

        sr = session._sample_rate
        duration = len(buffer) / sr

        # 1. 音高检测 (librosa PYIN)
        try:
            f0, voiced, _ = librosa.pyin(
                buffer.astype(np.float64), fmin=65.0, fmax=1047.0, sr=sr, hop_length=512
            )
            valid = f0[~np.isnan(f0)]
            detection_rate = len(valid) / max(len(f0), 1) if len(f0) > 0 else 0
            pitch_score = min(100, max(0, detection_rate * 80 + 20))
        except Exception:
            pitch_score = 50.0
            detection_rate = 0.0

        # 2. RMS 能量 (气息代理)
        try:
            rms = librosa.feature.rms(y=buffer.astype(np.float64), frame_length=2048, hop_length=512)[0]
            rms_cv = float(np.std(rms) / (np.mean(rms) + 1e-10))
            breath_score = min(100, max(0, 100 - rms_cv * 50))
        except Exception:
            breath_score = 50.0

        # 3. 节奏 (onset 密度)
        try:
            onset_env = librosa.onset.onset_strength(y=buffer.astype(np.float64), sr=sr)
            onsets = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr)
            onset_density = len(onsets) / max(duration, 1)
            rhythm_score = min(100, max(0, 50 + (onset_density - 2) * 10))
        except Exception:
            rhythm_score = 50.0

        # 4. 其他维度 (中性分)
        technique_score = 50.0
        muscle_score = 50.0
        artistry_score = 50.0

        # 六维加权
        total = (
            pitch_score * 0.10
            + rhythm_score * 0.10
            + breath_score * 0.20
            + technique_score * 0.25
            + muscle_score * 0.25
            + artistry_score * 0.10
        )

        # 等级判定
        if total >= 88:
            level, grade = "专业级", "S"
        elif total >= 78:
            level, grade = "优秀", "A"
        elif total >= 62:
            level, grade = "良好", "B"
        elif total >= 45:
            level, grade = "中等", "C"
        elif total >= 25:
            level, grade = "及格", "D"
        else:
            level, grade = "待改进", "E"

        return {
            "total_score": round(float(total), 1),
            "scores": {
                "pitch": round(pitch_score, 1),
                "rhythm": round(rhythm_score, 1),
                "breath": round(breath_score, 1),
                "technique": round(technique_score, 1),
                "muscle_strength": round(muscle_score, 1),
                "artistry": round(artistry_score, 1),
            },
            "timbre_adjustment": 0.0,
            "level": level,
            "grade": grade,
            "advice": [],
        }

    @staticmethod
    def _is_json(data: bytes) -> bool:
        """检测消息是否为 JSON (以 '{' 开头)"""
        return len(data) > 0 and data[0] == 0x7B  # '{'
