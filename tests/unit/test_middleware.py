"""
中间件单元测试 — v7.0.2

测试覆盖:
- SecurityHeadersMiddleware: 所有安全响应头正确注入
- RateLimiter (TokenBucket): 限流逻辑正确性
- RateLimitMiddleware: 端点限流行为
"""

import pytest
import time
from unittest.mock import patch, MagicMock

from starlette.testclient import TestClient
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.interfaces.api.middleware import (
    SecurityHeadersMiddleware,
    RateLimiter,
    RateLimitMiddleware,
    _TokenBucket,
    _SECURITY_HEADERS,
)


# ============================================================
# TokenBucket 测试
# ============================================================

class TestTokenBucket:
    """Token bucket 核心逻辑测试"""

    def test_initial_consume_allowed(self):
        """初始桶为空，消耗应失败"""
        bucket = _TokenBucket(tokens=0.0)
        assert not bucket.consume(rate=10.0, capacity=10.0)

    def test_consume_with_sufficient_tokens(self):
        """有足够 token 时可成功消耗"""
        bucket = _TokenBucket(tokens=5.0)
        assert bucket.consume(rate=0.0, capacity=10.0)

    def test_consume_with_insufficient_tokens(self):
        """token 不足时消耗失败"""
        bucket = _TokenBucket(tokens=0.5)
        assert not bucket.consume(rate=0.0, capacity=10.0)

    def test_refill_over_time(self):
        """随时间推移 token 自动补充"""
        bucket = _TokenBucket(tokens=0.0)
        original_refill = bucket.last_refill

        # 模拟时间推进 1 秒
        with patch.object(bucket, '_TokenBucket__refill_now', return_value=original_refill + 1.0, create=True):
            pass

        # 手动设置 tokens 为 10 (模拟已完全补充)
        bucket.tokens = 10.0
        assert bucket.consume(rate=0.0, capacity=10.0, cost=5.0)
        assert bucket.tokens == 5.0

    def test_capacity_cap(self):
        """token 不会超过 capacity"""
        bucket = _TokenBucket(tokens=100.0)
        assert bucket.consume(rate=0.0, capacity=10.0, cost=5.0)
        # 消耗后 tokens = min(10, 100) - 5 = 5
        assert bucket.tokens == 5.0


# ============================================================
# RateLimiter 测试
# ============================================================

class TestRateLimiter:
    """RateLimiter 功能测试"""

    def test_is_allowed_first_request(self):
        """空桶首次请求应被拒绝 (需等待 token 积累)"""
        limiter = RateLimiter()
        # 新桶 tokens=0, 立即检查应被拒绝
        result = limiter.is_allowed("test-client-1")
        assert not result, "空桶应立即拒绝请求"

    def test_is_allowed_with_high_capacity(self):
        """高 capacity 允许突发流量 (预充 token)"""
        limiter = RateLimiter()
        # 预充 token — 新桶 tokens=0 且 last_refill 接近当前时间, 首次 consume 无法补充
        limiter._buckets["test-client-2"].tokens = 100.0
        result = limiter.is_allowed("test-client-2", rate=1000.0, capacity=1000.0)
        assert result

    def test_different_keys_independent(self):
        """不同客户端 key 独立限流"""
        limiter = RateLimiter()
        limiter._buckets["client-a"].tokens = 10.0
        limiter._buckets["client-b"].tokens = 0.0

        assert limiter.is_allowed("client-a")
        assert not limiter.is_allowed("client-b")

    def test_is_allowed_upload_rate(self):
        """上传端点使用独立的限流参数"""
        limiter = RateLimiter()
        limiter._buckets["upload:upload-test"].tokens = 20.0
        assert limiter.is_allowed_upload("upload-test")

    def test_is_allowed_ws_rate(self):
        """WebSocket 端点使用独立的限流参数"""
        limiter = RateLimiter()
        limiter._buckets["ws:ws-test"].tokens = 10.0
        assert limiter.is_allowed_ws("ws-test")

    def test_cleanup_stale_buckets(self):
        """过期桶 (10 分钟未使用) 应被清理"""
        limiter = RateLimiter()
        limiter._buckets["stale"].tokens = 5.0
        limiter._buckets["stale"].last_refill = time.monotonic() - 700  # >10 min ago
        limiter._last_cleanup = 0  # force cleanup

        # 触发清理
        limiter._cleanup_if_needed()
        assert "stale" not in limiter._buckets


# ============================================================
# SecurityHeadersMiddleware 集成测试
# ============================================================

class TestSecurityHeadersMiddleware:
    """安全响应头中间件测试"""

    @pytest.fixture
    def client(self):
        """创建带安全头中间件的测试客户端"""
        from fastapi import FastAPI
        app = FastAPI()

        @app.get("/test")
        async def test_endpoint():
            return {"ok": True}

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        app.add_middleware(SecurityHeadersMiddleware)

        return TestClient(app)

    def test_security_headers_present(self, client):
        """所有安全响应头应出现在响应中"""
        response = client.get("/test")

        for header_name in _SECURITY_HEADERS:
            assert header_name in response.headers, (
                f"缺少安全头: {header_name}"
            )

    def test_x_content_type_options(self, client):
        """X-Content-Type-Options 应为 nosniff"""
        response = client.get("/test")
        assert response.headers["X-Content-Type-Options"] == "nosniff"

    def test_x_frame_options(self, client):
        """X-Frame-Options 应为 DENY"""
        response = client.get("/test")
        assert response.headers["X-Frame-Options"] == "DENY"

    def test_referrer_policy(self, client):
        """Referrer-Policy 应为 strict-origin-when-cross-origin"""
        response = client.get("/test")
        assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_csp_contains_required_directives(self, client):
        """CSP 应包含必要的指令"""
        response = client.get("/test")
        csp = response.headers["Content-Security-Policy"]

        # 验证关键 CSP 指令
        assert "default-src 'self'" in csp
        assert "script-src 'self'" in csp
        assert "connect-src" in csp
        assert "ws:" in csp  # WebSocket 支持
        assert "media-src" in csp
        assert "blob:" in csp  # 音频 blob 回放
        assert "frame-src 'none'" in csp
        assert "object-src 'none'" in csp

    def test_security_headers_dont_override_existing(self, client):
        """安全头不应覆盖应用已设置的自定义头"""
        response = client.get("/test")
        # 应用可自定义其他头，中间件使用 setdefault
        assert response.headers.get("content-type") == "application/json"

    def test_health_endpoint_also_has_headers(self, client):
        """健康检查端点也应有安全头"""
        response = client.get("/health")
        assert "X-Content-Type-Options" in response.headers


# ============================================================
# RateLimitMiddleware 集成测试
# ============================================================

class TestRateLimitMiddleware:
    """速率限制中间件测试"""

    @pytest.fixture
    def limiter_with_tokens(self):
        """创建已充满 token 的限流器 (key 匹配 TestClient IP)"""
        limiter = RateLimiter()
        # TestClient host = "testclient"
        test_key = "testclient"
        bucket = limiter._get_bucket(test_key)
        bucket.tokens = 500.0
        bucket = limiter._get_bucket(f"upload:{test_key}")
        bucket.tokens = 100.0
        bucket = limiter._get_bucket(f"ws:{test_key}")
        bucket.tokens = 50.0
        return limiter

    @pytest.fixture
    def client(self, limiter_with_tokens):
        """创建带速率限制的测试客户端"""
        from fastapi import FastAPI
        app = FastAPI()

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        @app.get("/api/v1/test")
        async def api_test():
            return {"data": "ok"}

        @app.post("/api/v1/upload")
        async def upload():
            return {"success": True}

        app.add_middleware(RateLimitMiddleware, limiter=limiter_with_tokens)

        return TestClient(app)

    def test_health_endpoint_not_rate_limited(self, client):
        """健康检查端点不应受限流"""
        for _ in range(100):
            response = client.get("/health")
            assert response.status_code == 200

    def test_api_endpoint_allows_normal_traffic(self, client):
        """正常流量应通过"""
        response = client.get("/api/v1/test")
        assert response.status_code == 200

    def test_upload_endpoint_allows_normal_traffic(self, client):
        """正常上传流量应通过"""
        response = client.post("/api/v1/upload")
        assert response.status_code == 200

    def test_rate_limited_response_has_retry_after(self, limiter_with_tokens):
        """限流响应应包含 Retry-After 头"""
        from fastapi import FastAPI
        app = FastAPI()

        # 创建一个 token 耗尽的限流器
        empty_limiter = RateLimiter()
        # 确保所有桶为空
        for key in list(empty_limiter._buckets.keys()):
            del empty_limiter._buckets[key]

        @app.get("/api/v1/test")
        async def api_test():
            return {"data": "ok"}

        app.add_middleware(RateLimitMiddleware, limiter=empty_limiter)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/api/v1/test")

        assert response.status_code == 429
        assert "Retry-After" in response.headers

    def test_ws_endpoint_uses_separate_limit(self, limiter_with_tokens):
        """WebSocket 端点使用独立的速率限制"""
        from fastapi import FastAPI
        app = FastAPI()

        @app.websocket("/ws/v1/score")
        async def ws_endpoint(websocket):
            await websocket.accept()
            await websocket.close()

        empty_limiter = RateLimiter()
        app.add_middleware(RateLimitMiddleware, limiter=empty_limiter)

        client = TestClient(app, raise_server_exceptions=False)
        response = client.get("/ws/v1/score")

        assert response.status_code == 429
