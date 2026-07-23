"""
FastAPI 应用入口 — v7.0 Phase 2

ADR-1: freeze_support() 防止嵌入式 Python 子进程递归崩溃
ADR-3: --export-openapi 导出 shared/openapi.json
ADR-4: 绞杀者模式 — 旧 Flask 挂载到 /old, 新 FastAPI 路由到 /api/v1
"""

from __future__ import annotations

import multiprocessing
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

# 确保项目根目录在 Python 路径中 (支持直接运行 backend/main.py)
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# ⚠️ 必须在任何 spawn 操作前调用
multiprocessing.freeze_support()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware


def _detect_gpu() -> dict:
    """检测 GPU 加速可用性"""
    import logging
    logger = logging.getLogger(__name__)
    info: dict = {
        "available": False,
        "device": None,
        "name": None,
        "demucs_accelerated": False,
    }
    try:
        import torch
        if torch.cuda.is_available():
            info["available"] = True
            info["device"] = "cuda"
            info["name"] = torch.cuda.get_device_name(0)
            info["demucs_accelerated"] = True
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            info["available"] = True
            info["device"] = "mps"
            info["name"] = "Apple Silicon GPU"
            info["demucs_accelerated"] = True
    except ImportError:
        logger.debug("PyTorch not available — GPU acceleration disabled")
    except Exception:
        logger.warning("GPU detection failed", exc_info=True)
    return info


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # startup
    gpu_info = _detect_gpu()
    app.state.gpu = gpu_info
    import time as _time
    app.state.started_at = _time.time()
    import logging
    logging.getLogger(__name__).info("GPU: %s", gpu_info)

    yield

    # shutdown: 清理资源


def create_app() -> FastAPI:
    """FastAPI 应用工厂 — 绞杀者模式主入口"""
    app = FastAPI(
        title="VAS v7.0",
        version="7.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS: Electron/开发模式不限源，生产 Web 部署需配置具体 origin
    # 注意: allow_credentials=True 与 allow_origins=["*"] 不兼容，
    # 当前应用不使用 Cookie/JWT 认证，故设置为 False
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ===== v7.0.2: 安全中间件 =====
    from backend.interfaces.api.middleware import (
        SecurityHeadersMiddleware,
        RateLimitMiddleware,
    )
    # 安全响应头 (CSP, X-Content-Type-Options, X-Frame-Options, etc.)
    app.add_middleware(SecurityHeadersMiddleware)
    # 速率限制 (全局 120/min, 上传 20/min, WebSocket 10/min)
    app.add_middleware(RateLimitMiddleware)

    # ===== Phase 2: 注册 FastAPI REST 路由 =====
    from backend.interfaces.api.routes.health import router as health_router
    from backend.interfaces.api.routes.assessment import router as assessment_router
    from backend.interfaces.api.routes.history import router as history_router
    from backend.interfaces.api.routes.audio import router as audio_router
    from backend.interfaces.api.routes.songs import router as songs_router

    app.include_router(health_router, tags=["health"])
    app.include_router(assessment_router, prefix="/api/v1", tags=["assessment"])
    app.include_router(history_router, prefix="/api/v1", tags=["history"])
    app.include_router(audio_router, prefix="/api/v1", tags=["audio"])
    app.include_router(songs_router, prefix="/api/v1", tags=["songs"])

    # ===== Phase 3: 注册 WebSocket 路由 =====
    from backend.interfaces.ws import router as ws_router
    app.include_router(ws_router)

    # ===== 绞杀者模式: 挂载旧 Flask =====
    from backend.legacy.flask_app import get_flask_app
    flask_app = get_flask_app()
    app.mount("/old", WSGIMiddleware(flask_app))

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 0))
    if "--port=0" in sys.argv:
        port = 0

    # --export-openapi: 导出 openapi.json 到 stdout (ADR-3)
    if "--export-openapi" in sys.argv:
        import json
        print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))
        sys.exit(0)

    if port == 0:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

    print(f"PORT={port}", flush=True)

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        workers=1,
        log_level="info",
    )
