"""
Pydantic Schemas — Auth 相关
=============================
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import OAuthProvider, SubscriptionTier


# ──────────────────────────────────────────────
# 基础
# ──────────────────────────────────────────────
class UserBase(BaseModel):
    """用户基础字段"""
    email: EmailStr
    name: str | None = Field(default=None, max_length=100)
    age: int | None = Field(default=None, ge=0, le=120)
    preferred_language: str = Field(default="zh-CN", max_length=10)


# ──────────────────────────────────────────────
# 注册 / 登录
# ──────────────────────────────────────────────
class SignupRequest(UserBase):
    """注册请求"""
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str | None = None  # 可选,前端校验


class LoginRequest(BaseModel):
    """登录请求"""
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class RefreshRequest(BaseModel):
    """刷新 token 请求"""
    refresh_token: str = Field(min_length=10)


# ──────────────────────────────────────────────
# 响应
# ──────────────────────────────────────────────
class UserResponse(BaseModel):
    """用户信息响应 (不包含密码)"""
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    name: str | None = None
    age: int | None = None
    is_senior: bool = False
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE
    oauth_provider: OAuthProvider = OAuthProvider.LOCAL
    oauth_id: str | None = None
    preferred_language: str = "zh-CN"
    is_active: bool = True
    is_verified: bool = False
    last_login_at: datetime | None = None
    created_at: datetime

    @field_validator("id", mode="before")
    @classmethod
    def _id_to_str(cls, v):
        """UUID → str (Pydantic 不自动转)"""
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class TokenResponse(BaseModel):
    """Token 响应 (登录/注册/刷新)"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # access token 剩余秒数
    user: UserResponse


class MessageResponse(BaseModel):
    """通用消息响应"""
    message: str
    detail: str | None = None
