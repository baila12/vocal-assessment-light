"""
Flask 速率限制装饰器 — v7.x (strangler pattern)

为 Flask /old/api/* 路由提供简易 in-memory 速率限制。
Flask 正在被 FastAPI 逐步替换，因此此模块保持最小化：
- 基于 dict 的 token bucket（无需 Redis）
- @rate_limit(max_requests, window_seconds) 装饰器
- 按客户端 IP 跟踪 (request.remote_addr)
- 通过 VAS_DISABLE_RATE_LIMIT=1 环境变量禁用（测试用）
- 超出限制时返回 429 JSON 错误响应
"""

from __future__ import annotations

import logging
import os
import threading
import time
from functools import wraps
from typing import Callable

from flask import jsonify, request

logger = logging.getLogger(__name__)

# ---- Token Bucket ----

class _TokenBucket:
    """线程安全的 token bucket"""

    def __init__(self, capacity: float, fill_rate: float) -> None:
        self._capacity = capacity
        self._fill_rate = fill_rate  # tokens per second
        self._tokens = capacity
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()

    def consume(self, cost: float = 1.0) -> bool:
        """尝试消耗 1 个 token。返回 True 放行，False 限流。"""
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_refill
            self._tokens = min(self._capacity, self._tokens + elapsed * self._fill_rate)
            self._last_refill = now

            if self._tokens >= cost:
                self._tokens -= cost
                return True
            return False


# ---- Rate Limiter ----

class _RateLimiter:
    """In-memory 速率限制器 — 按 (route_key, ip) 分桶"""

    def __init__(self) -> None:
        self._buckets: dict[str, _TokenBucket] = {}
        self._lock = threading.Lock()
        self._last_cleanup = time.monotonic()

    def _make_key(self, route: str, ip: str) -> str:
        return f"{route}|{ip}"

    def is_allowed(self, route: str, ip: str, max_requests: int, window_seconds: int) -> bool:
        """检查该 IP 对该路由是否允许"""
        key = self._make_key(route, ip)
        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                # fill_rate = max_requests / window_seconds, capacity = max_requests
                fill_rate = max_requests / float(window_seconds)
                bucket = _TokenBucket(capacity=float(max_requests), fill_rate=fill_rate)
                self._buckets[key] = bucket
            self._cleanup_if_needed()

        return bucket.consume()

    def _cleanup_if_needed(self) -> None:
        """定期清理过期桶（每 5 分钟，10 分钟未使用视为过期）"""
        now = time.monotonic()
        if now - self._last_cleanup < 300:
            return
        # double-check 在 _lock 外曾检查过，但 _lock 内操作更安全
        stale_keys = [
            k for k, b in self._buckets.items()
            if now - b._last_refill > 600
        ]
        for k in stale_keys:
            del self._buckets[k]
        self._last_cleanup = now
        if stale_keys:
            logger.debug("RateLimiter: cleaned up %d stale buckets", len(stale_keys))


_limiter = _RateLimiter()


# ---- Public API ----

def _is_disabled() -> bool:
    return os.environ.get("VAS_DISABLE_RATE_LIMIT") == "1"


def rate_limit(max_requests: int, window_seconds: int) -> Callable:
    """
    Flask 路由的速率限制装饰器。

    用法:
        @rate_limit(20, 60)  # 每分钟 20 次
        @upload_bp.route('/upload', methods=['POST'])
        def upload_file():
            ...

    超出限制时返回:
        HTTP 429 {"error":"Too Many Requests","detail":"请求过于频繁，请稍等 X 秒后重试"}
    """
    def decorator(f: Callable) -> Callable:
        route_name = f.__name__

        @wraps(f)
        def wrapper(*args, **kwargs):
            if _is_disabled():
                return f(*args, **kwargs)

            client_ip = request.remote_addr or "127.0.0.1"

            if not _limiter.is_allowed(route_name, client_ip, max_requests, window_seconds):
                logger.warning(
                    "Rate limit exceeded: route=%s ip=%s limit=%d/%ds",
                    route_name, client_ip, max_requests, window_seconds,
                )
                return (
                    jsonify({
                        "error": "Too Many Requests",
                        "detail": f"请求过于频繁，请稍等 {window_seconds} 秒后重试",
                    }),
                    429,
                    {"Retry-After": str(window_seconds)},
                )

            return f(*args, **kwargs)

        return wrapper
    return decorator
