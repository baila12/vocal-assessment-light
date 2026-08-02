"""健康检查路由"""

from fastapi import APIRouter
import time

router = APIRouter()


@router.get("/health")
async def health_check():
    """系统健康检查"""
    from backend.main import _detect_gpu

    gpu_info = _detect_gpu()
    return {
        "status": "healthy",
        "version": "7.8.0",
        "timestamp": time.time(),
        "gpu": gpu_info,
    }
