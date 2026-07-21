"""
安全工具 — 密码哈希 + JWT 编解码
=================================
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union

import jwt
from passlib.context import CryptContext

from app.core.config import settings

# ──────────────────────────────────────────────
# 密码哈希
# ──────────────────────────────────────────────
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=settings.bcrypt_rounds,
)


def hash_password(plain: str) -> str:
    """bcrypt 哈希"""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """bcrypt 验证"""
    try:
        return pwd_context.verify(plain, hashed)
    except Exception:
        return False


# ──────────────────────────────────────────────
# JWT
# ──────────────────────────────────────────────
def create_access_token(
    subject: str | int,
    extra_claims: Optional[dict[str, Any]] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    """创建 access token (短命,默认 30min)"""
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": str(subject),
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "iss": settings.jwt_issuer,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: str | int,
    extra_claims: Optional[dict[str, Any]] = None,
    expires_days: Optional[int] = None,
) -> str:
    """创建 refresh token (长命,默认 7d)"""
    expire = datetime.now(timezone.utc) + timedelta(
        days=expires_days or settings.jwt_refresh_token_expire_days
    )
    payload = {
        "sub": str(subject),
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "exp": expire,
        "iss": settings.jwt_issuer,
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str, expected_type: Optional[str] = None) -> dict[str, Any]:
    """
    解码 JWT,返回 payload dict
    - 验证签名 + 过期时间
    - 可选验证 token 类型 (access/refresh)
    - 失败抛 jwt.PyJWTError
    """
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
    )
    if expected_type and payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(
            f"Token type mismatch: expected={expected_type}, got={payload.get('type')}"
        )
    return payload


def create_token_pair(subject: str | int, extra_claims: Optional[dict] = None) -> dict[str, str]:
    """生成 access + refresh token 对"""
    return {
        "access_token": create_access_token(subject, extra_claims),
        "refresh_token": create_refresh_token(subject, extra_claims),
        "token_type": "bearer",
    }
