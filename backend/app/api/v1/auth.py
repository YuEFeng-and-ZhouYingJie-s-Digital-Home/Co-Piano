"""
Auth API — 注册 / 登录 / 刷新
==============================
"""
import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.base import get_async_db
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SignupRequest,
    TokenResponse,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["auth"])


def _build_token_response(user) -> TokenResponse:
    """构造 TokenResponse,自动加上 expires_in"""
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/signup",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册新用户",
)
async def signup(
    body: SignupRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    # 二次确认密码 (前端已校验,后端兜底)
    if body.confirm_password and body.confirm_password != body.password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match",
        )

    try:
        user = await UserService.create(
            db,
            email=body.email,
            password=body.password,
            name=body.name,
            age=body.age,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )

    return _build_token_response(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="登录 (返回 JWT pair)",
)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    user = await UserService.authenticate(db, body.email, body.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _build_token_response(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="用 refresh token 换新 access token",
)
async def refresh(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired, please login again",
        )
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid refresh token: {e}",
        )

    import uuid
    try:
        user_id = uuid.UUID(payload.get("sub"))
    except (ValueError, TypeError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid subject",
        )

    user = await UserService.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    return _build_token_response(user)


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="登出 (前端清掉 token 即可,后端无状态)",
)
async def logout() -> MessageResponse:
    """JWT 无状态,登出由前端清 localStorage。

    如需服务端吊销,需引入 Redis 黑名单 (A4.7 或后续)
    """
    return MessageResponse(
        message="Logged out",
        detail="Please discard the token on client side",
    )
