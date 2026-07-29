"""
Request ID 中间件
==================

为每个 HTTP 请求生成唯一 ID,贯穿日志,方便追踪
"""
from __future__ import annotations

import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """为每个请求生成/继承 X-Request-ID,并记录访问日志"""

    HEADER_NAME = "X-Request-ID"

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # 1. 继承或生成 request_id
        request_id = request.headers.get(self.HEADER_NAME) or self._generate_id()
        request.state.request_id = request_id

        # 2. 绑定到 structlog contextvars (整个请求链路日志都带这个 ID)
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        # 3. 计时 + 记录请求
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request_error",
                duration_ms=round(duration_ms, 2),
                error=str(exc),
            )
            structlog.contextvars.clear_contextvars()
            raise

        # 4. 记录响应
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers[self.HEADER_NAME] = request_id

        # 访问日志(JSON)
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_ip=request.client.host if request.client else None,
        )

        # 5. 清理 contextvars
        structlog.contextvars.clear_contextvars()
        return response

    @staticmethod
    def _generate_id() -> str:
        return f"req_{uuid.uuid4().hex[:16]}"
