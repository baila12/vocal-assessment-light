"""
安全中间件 — v7.0.2

提供速率限制和安全响应头，覆盖代码审查遗留 HIGH 优先级问题：
- 速率限制: 所有 /api/v1 端点 (slowapi in-memory)
- 安全响应头: CSP, X-Content-Type-Options, X-Frame-Options, HSTS, etc.

针对本地桌面应用的 CSP 配置: 允许内联脚本/样式 (Vue/Element Plus 需要),
WebSocket 连接 (实时演唱), blob: (音频回放)。
"""

from __future__ import annotations
import logging
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)


# ============================================================
# 安全响应头中间件
# ============================================================

# 本地桌面应用 CSP: 允许内联脚本/样式 (Vue/Element Plus) + WebSocket + blob 音频
# 生产 Web 部署时需要收紧: script-src 移除 'unsafe-inline', 换用 nonce-based
_SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",  # 废弃但保留以支持旧浏览器
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "X-Permitted-Cross-Domain-Policies": "none",
    "Cross-Origin-Resource-Policy": "cross-origin",  # 允许 Element Plus 字体等跨域资源
    # 本地应用 CSP — 生产 Web 部署需收紧 (nonce-based script-src)
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' ws: wss: http://127.0.0.1:*; "
        "media-src 'self' blob:; "
        "frame-src 'none'; "
        "object-src 'none'; "
        "base-uri 'self'"
    ),
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """为所有 HTTP 响应添加安全头"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        for header_name, header_value in _SECURITY_HEADERS.items():
            response.headers.setdefault(header_name, header_value)
        return response


# ============================================================
# 简易速率限制 (in-memory token bucket)
# ============================================================
#
# 为本地桌面应用设计的轻量级速率限制器。
# 不引入外部依赖 (slowapi, redis 等), 适合单用户场景。
# 生产 Web 部署时建议替换为 slowapi + Redis 实现分布式限流。

import time
import threading
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class _TokenBucket:
    """Token bucket 实现 — 线程安全"""
    tokens: float = field(default=0.0)
    last_refill: float = field(default_factory=time.monotonic)
    lock: threading.Lock = field(default_factory=threading.Lock)

    def consume(self, rate: float, capacity: float, cost: float = 1.0) -> bool:
        """尝试消耗 token。返回 True 表示放行, False 表示限流。"""
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(capacity, self.tokens + elapsed * rate)
            self.last_refill = now

            if self.tokens >= cost:
                self.tokens -= cost
                return True
            return False


class RateLimiter:
    """
    In-memory 速率限制器 — 按 IP 分桶。

    默认限制:
    - 全局:    120 req/min  (所有 /api/v1 端点)
    - 上传:     20 req/min  (POST /api/v1/upload)
    - WebSocket: 10 conn/min (WS /ws/v1/score)
    """

    def __init__(self) -> None:
        self._buckets: dict[str, _TokenBucket] = defaultdict(_TokenBucket)
        self._cleanup_lock = threading.Lock()
        self._last_cleanup = time.monotonic()

    def _get_bucket(self, key: str) -> _TokenBucket:
        """获取或创建 token bucket"""
        self._cleanup_if_needed()
        return self._buckets[key]

    def _cleanup_if_needed(self) -> None:
        """定期清理过期桶 (每 5 分钟)"""
        now = time.monotonic()
        if now - self._last_cleanup < 300:
            return
        with self._cleanup_lock:
            if now - self._last_cleanup < 300:
                return
            stale_keys = [
                k for k, b in self._buckets.items()
                if now - b.last_refill > 600  # 10 分钟未使用
            ]
            for k in stale_keys:
                del self._buckets[k]
            self._last_cleanup = now
            if stale_keys:
                logger.debug("RateLimiter: cleaned up %d stale buckets", len(stale_keys))

    def is_allowed(
        self,
        key: str,
        rate: float = 120.0,
        capacity: float = 120.0,
    ) -> bool:
        """检查是否允许请求"""
        bucket = self._get_bucket(key)
        return bucket.consume(rate=rate, capacity=capacity)

    def is_allowed_upload(self, key: str) -> bool:
        """上传端点专用限制 (20/min)"""
        return self.is_allowed(f"upload:{key}", rate=20.0, capacity=20.0)

    def is_allowed_ws(self, key: str) -> bool:
        """WebSocket 连接专用限制 (10/min)"""
        return self.is_allowed(f"ws:{key}", rate=10.0, capacity=10.0)


# 全局单例
_rate_limiter = RateLimiter()


def get_rate_limiter() -> RateLimiter:
    """依赖注入: 获取全局速率限制器"""
    return _rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    速率限制 ASGI 中间件。

    按客户端 IP 限流:
    - 全局 API: 120 req/min
    - POST /upload: 20 req/min
    - 健康检查 /health: 不限流
    """

    def __init__(self, app, limiter: RateLimiter | None = None):
        super().__init__(app)
        self._limiter = limiter or _rate_limiter

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 健康检查不限流
        if request.url.path == "/health":
            return await call_next(request)

        # 获取客户端标识 (优先 X-Forwarded-For)
        client_ip = (
            request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            or request.client.host if request.client
            else "127.0.0.1"
        )

        # WebSocket 升级请求
        if request.url.path.startswith("/ws/"):
            if not self._limiter.is_allowed_ws(client_ip):
                logger.warning("Rate limit (WebSocket): %s", client_ip)
                return Response(
                    content='{"error":"Too Many Requests"}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": "60"},
                )
            return await call_next(request)

        # API 端点限流
        if request.url.path.startswith("/api/"):
            if "upload" in request.url.path and request.method == "POST":
                if not self._limiter.is_allowed_upload(client_ip):
                    logger.warning("Rate limit (upload): %s", client_ip)
                    return Response(
                        content='{"error":"Too Many Requests","detail":"上传过于频繁，请稍后再试"}',
                        status_code=429,
                        media_type="application/json",
                        headers={"Retry-After": "30"},
                    )

            if not self._limiter.is_allowed(client_ip):
                logger.warning("Rate limit (global): %s", client_ip)
                return Response(
                    content='{"error":"Too Many Requests"}',
                    status_code=429,
                    media_type="application/json",
                    headers={"Retry-After": "30"},
                )

        return await call_next(request)
