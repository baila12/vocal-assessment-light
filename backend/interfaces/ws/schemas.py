"""
WebSocket 消息 Schema — v7.0 Phase 3

客户端→服务器: 二进制 PCM 帧 (4字节长度前缀) + JSON 控制帧
服务器→客户端: JSON 事件帧
"""

from __future__ import annotations
from typing import Optional, Literal
from pydantic import BaseModel, Field


class WsClientStart(BaseModel):
    """客户端→服务器: 开始录音"""
    type: Literal["start"] = "start"
    song_id: Optional[str] = None
    mode: Literal["quick", "professional"] = "quick"


class WsClientStop(BaseModel):
    """客户端→服务器: 停止录音"""
    type: Literal["stop"] = "stop"


class WsServerReady(BaseModel):
    """服务器→客户端: 连接就绪"""
    event: Literal["ready"] = "ready"
    session_id: str


class WsServerPitchUpdate(BaseModel):
    """服务器→客户端: 实时音高数据"""
    event: Literal["pitch_update"] = "pitch_update"
    frequencies: list[float]
    times: list[float]
    confidence: list[float]
    duration: float = 0.0


class WsServerPartialScore(BaseModel):
    """服务器→客户端: 增量评分 (每2秒)"""
    event: Literal["partial_score"] = "partial_score"
    pitch: float = 0.0
    rhythm: float = 0.0
    progress: float = 0.0  # 0.0-1.0
    elapsed_s: float = 0.0


class WsServerQualityWarning(BaseModel):
    """服务器→客户端: 录音质量警告"""
    event: Literal["quality_warning"] = "quality_warning"
    message: str
    level: Literal["low_volume", "noise", "clipping"] = "low_volume"


class WsServerFinalScore(BaseModel):
    """服务器→客户端: 最终六维评分"""
    event: Literal["final_score"] = "final_score"
    total: float = Field(ge=0, le=100)
    scores: dict[str, float] = Field(default_factory=dict)
    timbre_adjustment: float = 0.0
    level: str = ""
    grade: str = ""
    advice: list[str] = Field(default_factory=list)
    duration_s: float = 0.0


class WsServerError(BaseModel):
    """服务器→客户端: 错误"""
    event: Literal["error"] = "error"
    message: str
    recoverable: bool = False
