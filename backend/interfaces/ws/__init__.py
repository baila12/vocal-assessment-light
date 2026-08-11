"""WebSocket 路由注册"""

import logging

from fastapi import APIRouter, WebSocket

from backend.interfaces.ws.score_handler import ScoreWebSocketHandler

router = APIRouter()
logger = logging.getLogger(__name__)

# 单例 handler
_score_handler = ScoreWebSocketHandler()


@router.websocket("/ws/v1/score")
async def websocket_score(ws: WebSocket):
    """实时评分 WebSocket 端点

    协议 (ADR-7):
      - 客户端 → 服务器: 二进制帧 [4-byte BE uint32 len][Float32 PCM]
      - 客户端 → 服务器: JSON {"type":"start"|"stop"}
      - 服务器 → 客户端: JSON {"event":"ready"|"pitch_update"|"partial_score"|"final_score"|"error"}
    """
    try:
        await _score_handler.handle(ws)
    except Exception:
        # v7.14 审查 C1/E1: Starlette HTTP 全局异常处理器不覆盖 WebSocket 路由。
        # 端点层兜底 — 崩溃时先发错误帧再关闭, 避免客户端挂起。
        logger.exception("WS endpoint unhandled error")
        try:
            await ws.send_json({"event": "error", "message": "服务器内部错误，请重试"})
        except Exception:
            logger.exception("WS endpoint failed to send error frame")
        try:
            await ws.close(code=1011)
        except Exception:
            logger.exception("WS endpoint failed to close connection")
