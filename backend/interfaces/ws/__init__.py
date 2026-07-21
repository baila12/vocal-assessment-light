"""WebSocket 路由注册"""

from fastapi import APIRouter, WebSocket

from backend.interfaces.ws.score_handler import ScoreWebSocketHandler

router = APIRouter()

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
    await _score_handler.handle(ws)
