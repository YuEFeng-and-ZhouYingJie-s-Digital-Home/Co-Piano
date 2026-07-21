"""
全局异常处理中间件
====================

捕获未处理异常,统一 JSON 错误响应,带 request_id
"""
from __future__ import annotations

import os

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """注册到 FastAPI app"""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # HTTPException 已经是用户预期的(401/403/404/409),不需要 stack trace
        # 保留 FastAPI 默认的 detail 字段(向后兼容)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,  # FastAPI 默认格式,客户端代码可能依赖
                "error": "http_error",
                "status_code": exc.status_code,
                "message": exc.detail,
                "request_id": getattr(request.state, "request_id", None),
            },
            headers=exc.headers,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        """Pydantic 验证错误(422)"""
        errors = exc.errors()
        logger.warning(
            "validation_error",
            errors=errors[:5],  # 只记前 5 个,避免日志爆
            error_count=len(errors),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "error": "validation_error",
                "message": "Invalid request payload",
                "details": errors,
                "request_id": getattr(request.state, "request_id", None),
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        """未捕获的异常 → 500"""
        logger.exception(
            "unhandled_exception",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        # 生产环境不泄露内部错误细节
        message = str(exc) if os.getenv("DEBUG") else "Internal server error"
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "internal_server_error",
                "message": message,
                "request_id": getattr(request.state, "request_id", None),
            },
        )
