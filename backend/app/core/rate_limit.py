"""
限流 (slowapi)
================

策略:
- 默认 60 次/分钟/IP
- 登录/注册端点 5 次/分钟/IP(防爆破)
- LLM 反馈 10 次/分钟/用户(贵)
- 文件上传 20 次/小时/用户(防滥用)

key_func: 用 remote IP,登录用 IP+email 组合
storage: 内存(开发) / Redis(生产,A3.6 接)
"""
from __future__ import annotations

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address


def get_client_ip(request: Request) -> str:
    """获取客户端 IP(支持反向代理 X-Forwarded-For)"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return get_remote_address(request)


def get_auth_key(request: Request) -> str:
    """登录/注册用 IP 限流(更严)"""
    return f"auth:{get_client_ip(request)}"


# 全局限流器
limiter = Limiter(
    key_func=get_client_ip,
    default_limits=["60/minute"],
    headers_enabled=True,  # 加 X-RateLimit-* headers
    strategy="fixed-window",  # 简单 fixed window,生产用 moving-window 更平滑
)


# 常用限流策略(供路由装饰用)
RATE_LIMIT_DEFAULT = "60/minute"
RATE_LIMIT_AUTH = "5/minute"  # 登录/注册
RATE_LIMIT_FEEDBACK = "10/minute"  # LLM 反馈
RATE_LIMIT_UPLOAD = "20/hour"  # MIDI 上传


__all__ = [
    "limiter",
    "RateLimitExceeded",
    "get_client_ip",
    "get_auth_key",
    "RATE_LIMIT_DEFAULT",
    "RATE_LIMIT_AUTH",
    "RATE_LIMIT_FEEDBACK",
    "RATE_LIMIT_UPLOAD",
]
