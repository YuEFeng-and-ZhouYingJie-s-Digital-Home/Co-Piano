"""
Middleware tests — CORS / RequestID / RateLimit / Logging / ErrorHandler
======================================================================
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.rate_limit import limiter as global_limiter
from app.middleware.error_handler import register_exception_handlers
from app.middleware.request_id import RequestIDMiddleware


# ──────────────────────────────────────────────
# RequestIDMiddleware
# ──────────────────────────────────────────────
def test_request_id_generated_when_missing():
    """无 X-Request-ID → 自动生成"""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/ping")
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers
    rid = r.headers["X-Request-ID"]
    assert rid.startswith("req_")


def test_request_id_inherited_when_provided():
    """前端传 X-Request-ID → 透传"""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    client = TestClient(app)
    r = client.get("/ping", headers={"X-Request-ID": "client-trace-12345"})
    assert r.headers["X-Request-ID"] == "client-trace-12345"


def test_request_id_unique_per_request():
    """不同请求 → 不同 ID"""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/ping")
    async def ping():
        return {"ok": True}

    client = TestClient(app)
    r1 = client.get("/ping")
    r2 = client.get("/ping")
    assert r1.headers["X-Request-ID"] != r2.headers["X-Request-ID"]


# ──────────────────────────────────────────────
# ErrorHandler
# ──────────────────────────────────────────────
def test_http_exception_handler():
    """HTTPException 统一格式"""
    from fastapi import HTTPException
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    async def boom():
        raise HTTPException(status_code=404, detail="Not found")

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/boom")
    assert r.status_code == 404
    data = r.json()
    assert data["error"] == "http_error"
    assert data["status_code"] == 404
    assert data["message"] == "Not found"


def test_unhandled_exception_handler():
    """未捕获异常 → 500 + 不泄露细节(生产)"""
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/crash")
    async def crash():
        raise ValueError("Database connection lost")

    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/crash")
    assert r.status_code == 500
    data = r.json()
    assert data["error"] == "internal_server_error"
    assert "request_id" in data


def test_validation_error_handler():
    """Pydantic 422 验证错误统一格式"""
    from pydantic import BaseModel

    class Body(BaseModel):
        email: str
        age: int

    app = FastAPI()
    register_exception_handlers(app)

    @app.post("/validate")
    async def validate(body: Body):
        return {"ok": True}

    client = TestClient(app)
    r = client.post("/validate", json={"email": "not-an-email", "age": "not-a-number"})
    assert r.status_code == 422
    data = r.json()
    assert data["error"] == "validation_error"
    assert "details" in data
    assert data["message"] == "Invalid request payload"


# ──────────────────────────────────────────────
# RateLimit
# ──────────────────────────────────────────────
def test_rate_limit_headers_present():
    """rate-limited 端点返回 X-RateLimit-* headers"""
    from fastapi import Request
    from fastapi.responses import JSONResponse
    app = FastAPI()
    app.state.limiter = global_limiter
    app.add_middleware(RequestIDMiddleware)

    @app.get("/limited")
    @global_limiter.limit("2/minute")
    async def limited(request: Request):
        return JSONResponse(content={"ok": True})

    client = TestClient(app)
    r = client.get("/limited")
    assert r.status_code == 200
    headers_lower = {k.lower() for k in r.headers.keys()}
    assert any("ratelimit" in h for h in headers_lower) or any("rate-limit" in h for h in headers_lower)


def test_rate_limit_exceeded_returns_429():
    """超限 → 429"""
    from fastapi import Request
    app = FastAPI()
    app.state.limiter = Limiter(key_func=get_remote_address)
    app.add_middleware(RequestIDMiddleware)
    register_exception_handlers(app)

    @app.get("/limited")
    @app.state.limiter.limit("1/minute")
    async def limited(request: Request):
        return {"ok": True}

    client = TestClient(app)
    r1 = client.get("/limited")
    assert r1.status_code == 200

    # 第二次超限
    r2 = client.get("/limited")
    # slowapi 默认 429
    assert r2.status_code in (429, 403)


# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
def test_setup_logging_runs_without_error():
    """setup_logging 可重复调用不崩"""
    from app.core.logging import setup_logging, get_logger
    setup_logging()  # 第一次
    setup_logging()  # 第二次
    log = get_logger("test")
    log.info("test_event", key="value")
    # 不抛异常即通过


def test_get_logger_returns_bound_logger():
    """get_logger 返回可用的 logger"""
    from app.core.logging import get_logger
    log = get_logger("copiano.test")
    # structlog BoundLogger 有 .info / .warning / .error / .bind 等方法
    assert hasattr(log, "info")
    assert hasattr(log, "warning")
    assert hasattr(log, "error")
    assert hasattr(log, "bind")


# ──────────────────────────────────────────────
# 集成测试 — 完整 app 启动 + middleware 协同
# ──────────────────────────────────────────────
def test_full_app_health_returns_request_id():
    """完整 app 启动后,/health 返回 X-Request-ID"""
    from main import app
    client = TestClient(app)
    r = client.get("/health")
    assert r.status_code == 200
    assert "X-Request-ID" in r.headers
    assert r.json()["status"] == "ok"


def test_full_app_status_lists_middleware_module():
    """/api/v1/status 列出 middleware 模块"""
    from main import app
    client = TestClient(app)
    r = client.get("/api/v1/status")
    assert r.status_code == 200
    data = r.json()
    assert data["modules"]["middleware"] is True
    assert "middleware" in data


def test_full_app_cors_preflight():
    """CORS 预检请求正常"""
    from main import app
    client = TestClient(app)
    r = client.options(
        "/api/v1/auth/signup",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    # OPTIONS 应该 200/204
    assert r.status_code in (200, 204)
    # 应该有 CORS headers
    assert "access-control-allow-origin" in {k.lower() for k in r.headers.keys()}


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
