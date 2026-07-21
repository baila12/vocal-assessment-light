"""
FastAPI 应用入口 — v7.0

ADR-1: freeze_support() 防止嵌入式 Python 子进程递归崩溃
ADR-3: --export-openapi 导出 shared/openapi.json
"""

from __future__ import annotations

import multiprocessing
import os
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator

# ⚠️ 必须在任何 spawn 操作前调用
multiprocessing.freeze_support()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware


def _detect_gpu() -> dict:
    """检测 GPU 加速可用性"""
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
        pass
    except Exception:
        pass
    return info


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # startup
    gpu_info = _detect_gpu()
    app.state.gpu = gpu_info
    app.state.started_at = __import__("time").time()
    print(f"[VAS v7.0] GPU: {gpu_info}")

    yield

    # shutdown: 清理资源
    # Phase 2+ 添加: DB dispose, 模型缓存清理


def create_app() -> FastAPI:
    """FastAPI 应用工厂 — 绞杀者模式主入口"""
    app = FastAPI(
        title="VAS v7.0",
        version="7.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS: Electron 生产模式不限源 (localhost 随机端口)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Phase 2: 注册新路由
    # app.include_router(assessment.router, prefix="/api/v1", tags=["assessment"])
    # app.include_router(history.router, prefix="/api/v1", tags=["history"])
    # app.include_router(comparison.router, prefix="/api/v1", tags=["comparison"])
    # app.include_router(songs.router, prefix="/api/v1", tags=["songs"])

    # Phase 2: 挂载旧 Flask (绞杀者模式)
    # from backend.legacy.flask_app import flask_app
    # app.mount("/old", WSGIMiddleware(flask_app))

    @app.get("/health")
    async def health():
        """健康检查 — Phase 0 验收关键端点"""
        import time
        gpu_info = _detect_gpu()
        return {
            "status": "healthy",
            "version": "7.0.0",
            "timestamp": time.time(),
            "gpu": gpu_info,
        }

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    # --port=0: 让 OS 分配随机端口, stdout 打印 PORT=xxxxx (Electron 捕获)
    port = int(os.environ.get("PORT", 0))
    if "--port=0" in sys.argv:
        port = 0

    # --export-openapi: 导出 openapi.json 到 stdout (ADR-3)
    if "--export-openapi" in sys.argv:
        import json
        print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))
        sys.exit(0)

    if port == 0:
        # 获取随机端口后通知 Electron
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]

    print(f"PORT={port}", flush=True)  # Electron 捕获此行

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=port,
        workers=1,  # ⚠️ 硬锁定: 嵌入式 Python + multiprocessing 兼容性
        log_level="info",
    )
