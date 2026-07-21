"""
Users API — 当前用户信息
========================
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from app.api.deps import get_current_active_user
from app.models.user import User
from app.schemas.auth import UserResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="获取当前登录用户信息",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="更新当前用户资料 (name/age/preferred_language)",
)
async def update_me(
    name: Optional[str] = None,
    age: Optional[int] = None,
    preferred_language: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """简化版 PATCH,只允许更新几个非敏感字段"""
    if name is not None:
        current_user.name = name
    if age is not None:
        current_user.age = age
        # 重新评估银发模式
        if current_user.should_auto_senior():
            current_user.is_senior = True
    if preferred_language is not None:
        current_user.preferred_language = preferred_language
    return UserResponse.model_validate(current_user)
