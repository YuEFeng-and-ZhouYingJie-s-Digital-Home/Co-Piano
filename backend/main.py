"""
CoPiano v4 — FastAPI Backend
=============================

AI 古典钢琴教练 — 后端 API 服务

入口: `python main.py` 或 `uvicorn main:app --reload --port 8000`

作者: CoPiano Team
版本: v4.0 (Phase 7A W2 — A2.1)
日期: 2026-07-21
"""
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings

# ──────────────────────────────────────────────
# 日志配置
# ──────────────────────────────────────────────
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("copiano.api")

# ──────────────────────────────────────────────
# 应用元数据
# ──────────────────────────────────────────────
APP_TITLE = "CoPiano API"
APP_DESCRIPTION = """
CoPiano — AI 古典钢琴教练

## 功能
- 🎹 **5 维多模态评估**: pitch / expressiveness / hand_pose / rhythm / sight_reading
- 📚 **7 天自适应课程**: SM-2 spaced repetition + 弱点检测
- 👵 **银发模式**: 60+ 用户自动启用
- 🤖 **LLM 流式反馈**: Qwen 7B / OpenAI GPT-4
- 🎼 **视奏训练**: 4 难度 × 3 模式 × 3 输入

## 5 维评估
| 维度 | 权重 | 说明 |
|------|------|------|
| pitch | 20% | 音高准确度 |
| expressiveness | 25% | 表现力 (timing/dynamics/articulation/...) |
| hand_pose | 20% | 手型 (wrist/arch/curl/thumb/...) |
| rhythm | 20% | 节奏稳定性 |
| sight_reading | 15% | 视奏能力 |
"""
APP_VERSION = "4.0.0-alpha"
API_V1_PREFIX = "/api/v1"

# ──────────────────────────────────────────────
# 生命周期 (Lifespan)
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭钩子"""
    logger.info("🚀 CoPiano API starting (version=%s)", APP_VERSION)
    logger.info("📍 Environment: %s", os.getenv("ENV", "development"))
    yield
    logger.info("🛑 CoPiano API shutting down")


# ──────────────────────────────────────────────
# FastAPI 应用实例
# ──────────────────────────────────────────────
app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{API_V1_PREFIX}/openapi.json",
)

# ──────────────────────────────────────────────
# CORS 中间件
# ──────────────────────────────────────────────
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:3000,http://localhost:5173,https://copiano.com,https://app.copiano.com",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# 挂载 v1 路由
# ──────────────────────────────────────────────
app.include_router(api_router, prefix=API_V1_PREFIX)

# ──────────────────────────────────────────────
# 基础路由
# ──────────────────────────────────────────────
@app.get("/", tags=["meta"])
async def root():
    """根路径 - 服务信息"""
    return {
        "service": "CoPiano API",
        "version": APP_VERSION,
        "phase": "7A (Backend + Web)",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health",
        "api": API_V1_PREFIX,
    }


@app.get("/health", tags=["meta"])
async def health():
    """健康检查 (供 Nginx/load balancer 使用)"""
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": "copiano-api",
            "version": APP_VERSION,
        },
    )


@app.get(f"{API_V1_PREFIX}/ping", tags=["meta"])
async def ping():
    """简单 ping 端点 (用于监控和负载测试)"""
    return {"ping": "pong", "ts": "2026-07-21"}


# ──────────────────────────────────────────────
# API v1 路由占位符 (后续 A2.2-A4.8 填充)
# ──────────────────────────────────────────────
@app.get(f"{API_V1_PREFIX}/status", tags=["meta"])
async def api_v1_status():
    """v1 状态总览 — 列出已实现的模块"""
    return {
        "api_version": "v1",
        "modules": {
            "auth": True,         # ✅ A2.3 (signup/login/refresh/logout)
            "users": True,        # ✅ A2.3 (GET /me, PATCH /me)
            "evaluations": False, # A3.2-A3.4
            "curriculum": False,  # A4.2-A4.3
            "sight_reading": False, # A4.5
            "feedback": False,    # A4.7
            "senior_mode": False, # A4.6
            "subscription": False, # A5.x
        },
        "endpoints": {
            "POST /api/v1/auth/signup": "注册新用户",
            "POST /api/v1/auth/login": "登录 (返回 JWT pair)",
            "POST /api/v1/auth/refresh": "刷新 access token",
            "POST /api/v1/auth/logout": "登出",
            "GET /api/v1/users/me": "当前用户信息",
            "PATCH /api/v1/users/me": "更新资料 (name/age/lang)",
        },
        "next_task": "A2.4 — OAuth2 (Apple/Google)",
        "eta": "W2",
    }


# ──────────────────────────────────────────────
# 全局异常处理
# ──────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """兜底异常处理 (生产环境应避免泄露内部错误)"""
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": str(exc) if os.getenv("DEBUG") else "Internal server error",
        },
    )


# ──────────────────────────────────────────────
# 直接运行入口
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=os.getenv("DEBUG", "false").lower() == "true",
    )
