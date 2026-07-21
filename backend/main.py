"""
CoPiano v4 — FastAPI Backend
=============================

AI 古典钢琴教练 — 后端 API 服务

入口: `python main.py` 或 `uvicorn main:app --reload --port 8000`

作者: CoPiano Team
版本: v4.0 (Phase 7A W2 — A2.6)
日期: 2026-07-21
"""
import os
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.rate_limit import limiter
from app.middleware.error_handler import register_exception_handlers
from app.middleware.request_id import RequestIDMiddleware

# ──────────────────────────────────────────────
# 日志配置 (structlog)
# ──────────────────────────────────────────────
setup_logging()
logger = get_logger("copiano.api")

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
APP_VERSION = settings.app_version
API_V1_PREFIX = "/api/v1"

# ──────────────────────────────────────────────
# 生命周期 (Lifespan)
# ──────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭钩子"""
    logger.info("copiano_api_starting", version=APP_VERSION, env=settings.env)
    yield
    logger.info("copiano_api_shutting_down")


# ──────────────────────────────────────────────
# FastAPI 应用实例
# ──────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    description=APP_DESCRIPTION,
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{API_V1_PREFIX}/openapi.json",
)

# ──────────────────────────────────────────────
# 限流 (slowapi)
# ──────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ──────────────────────────────────────────────
# 中间件 (顺序很重要: 后加的先执行)
# ──────────────────────────────────────────────
# 1. CORS (最先,所有跨域请求都先过这里)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],  # 暴露给前端
)

# 2. Request ID (每个请求绑定 UUID,贯穿日志)
app.add_middleware(RequestIDMiddleware)

# 3. 全局异常处理 (最后兜底)
register_exception_handlers(app)

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


@app.get(f"{API_V1_PREFIX}/status", tags=["meta"])
async def api_v1_status():
    """v1 状态总览 — 列出已实现的模块"""
    return {
        "api_version": "v1",
        "modules": {
            "auth": True,         # ✅ A2.3
            "users": True,        # ✅ A2.3
            "oauth": True,        # ✅ A2.4
            "middleware": True,   # ✅ A2.6
            "alembic": True,      # ✅ A2.5
            "evaluations": True,  # ✅ A3.2-A3.4
            "curriculum": True,   # ✅ A4.2-A4.3 (7天课程 + mark complete)
            "sight_reading": True, # ✅ A4.5 (session + answer + 详情)
            "feedback": False,    # A4.7
            "senior_mode": False, # A4.6
            "subscription": False, # A5.x
        },
        "endpoints": {
            "POST /api/v1/auth/signup": "注册新用户",
            "POST /api/v1/auth/login": "登录 (返回 JWT pair)",
            "POST /api/v1/auth/refresh": "刷新 access token",
            "POST /api/v1/auth/logout": "登出",
            "POST /api/v1/auth/oauth/apple": "Apple Sign In",
            "POST /api/v1/auth/oauth/google": "Google Sign In",
            "POST /api/v1/auth/oauth/wechat": "WeChat 扫码登录",
            "GET /api/v1/auth/oauth/wechat/qrcode": "微信扫码 URL",
            "POST /api/v1/auth/oauth/link": "绑 OAuth 到当前用户",
            "POST /api/v1/auth/oauth/unlink": "解绑 OAuth",
            "GET /api/v1/users/me": "当前用户信息",
            "PATCH /api/v1/users/me": "更新资料 (name/age/lang)",
            "POST /api/v1/evaluations": "上传 MIDI → 5 维评估",
            "GET /api/v1/evaluations/{id}": "评估详情",
            "GET /api/v1/evaluations/history": "当前用户评估历史(分页)",
            "GET /api/v1/curriculum": "7 天课程(动态生成)",
            "GET /api/v1/curriculum/{day_num}": "某天课程详情",
            "POST /api/v1/curriculum/blocks/{id}/complete": "标记 block 完成",
            "POST /api/v1/sight-reading/session": "开始视奏会话",
            "POST /api/v1/sight-reading/session/{id}/answer": "提交答案 + 下一题",
            "GET /api/v1/sight-reading/session/{id}": "会话详情 + 统计",
        },
        "middleware": {
            "cors": settings.cors_origins_list,
            "rate_limit_default": "60/minute per IP",
            "request_id_header": "X-Request-ID",
            "logging": "JSON (production) / Console (development)",
        },
        "next_task": "A4.6 — senior_mode + LLM proxy",
        "eta": "W4",
    }


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
        log_config=None,  # 用我们自己的 structlog,不覆盖
    )
