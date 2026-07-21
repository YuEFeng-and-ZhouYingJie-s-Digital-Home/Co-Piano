"""
OAuth API — Apple / Google / WeChat 登录端点
=============================================

端点:
- POST /api/v1/auth/oauth/apple     Apple identity_token 登录
- POST /api/v1/auth/oauth/google    Google id_token 登录
- POST /api/v1/auth/oauth/wechat    WeChat code 登录
- POST /api/v1/auth/oauth/link      绑定 OAuth 到已登录用户
- POST /api/v1/auth/oauth/unlink    解绑 OAuth
- GET  /api/v1/auth/oauth/wechat/qrcode  微信扫码 URL

策略:
- OAuth 首次登录 → 自动注册新 user (email 优先)
- email 已在本地 → 合并到已有账户
- 返回 JWT pair (同 A2.3)
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token
from app.db.base import get_async_db
from app.models.user import OAuthProvider, User
from app.schemas.auth import TokenResponse, UserResponse
from app.schemas.oauth import (
    AppleCallbackRequest,
    GoogleCallbackRequest,
    OAuthLinkRequest,
    WeChatCallbackRequest,
)
from app.services import oauth_service

logger = logging.getLogger("copiano.oauth.api")

router = APIRouter(prefix="/auth/oauth", tags=["auth", "oauth"])


def _build_token_response(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


# ──────────────────────────────────────────────
# Apple Sign In
# ──────────────────────────────────────────────
@router.post(
    "/apple",
    response_model=TokenResponse,
    summary="Apple Sign In — 用 identity_token 登录/注册",
)
async def login_apple(
    body: AppleCallbackRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    """Apple Sign In 入口(适用于 Web + iOS)

    iOS 原生 ASAuthorizationAppleIDProvider 拿到 identityToken 后
    POST 到这里,后端验签 + upsert user
    """
    try:
        account = await oauth_service.verify_apple_id_token(
            body.id_token,
            expected_nonce=body.nonce,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    # 用 Apple 提供的 user_identifier 作为兜底(防止 JWT 验证路径不一致)
    if not account.provider_user_id:
        account.provider_user_id = body.user_identifier

    user = await oauth_service.get_or_create_oauth_user(db, account)
    return _build_token_response(user)


# ──────────────────────────────────────────────
# Google Sign In
# ──────────────────────────────────────────────
@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Google Sign In — 用 id_token 登录/注册",
)
async def login_google(
    body: GoogleCallbackRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    try:
        account = await oauth_service.verify_google_id_token(body.id_token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    user = await oauth_service.get_or_create_oauth_user(db, account)
    return _build_token_response(user)


# ──────────────────────────────────────────────
# WeChat (微信扫码登录)
# ──────────────────────────────────────────────
@router.get(
    "/wechat/qrcode",
    summary="生成微信扫码登录 URL",
)
async def wechat_qrcode(
    redirect_uri: str = Query(..., description="回调 URL,需在微信开放平台配置"),
    state: Optional[str] = Query(None, description="CSRF token"),
):
    """前端拿到 url 后转二维码,用户扫码后微信 redirect 到 redirect_uri?code=...&state=..."""
    try:
        url = oauth_service.build_wechat_authorize_url(redirect_uri, state)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    return {"authorize_url": url, "state": state}


@router.post(
    "/wechat",
    response_model=TokenResponse,
    summary="微信 code 登录 (前端拿到 code 后 POST)",
)
async def login_wechat(
    body: WeChatCallbackRequest,
    db: AsyncSession = Depends(get_async_db),
) -> TokenResponse:
    try:
        account = await oauth_service.wechat_exchange_code(body.code)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    user = await oauth_service.get_or_create_oauth_user(db, account)
    return _build_token_response(user)


# ──────────────────────────────────────────────
# 绑定 / 解绑
# ──────────────────────────────────────────────
@router.post(
    "/link",
    response_model=UserResponse,
    summary="把 OAuth 账户绑到当前已登录用户",
)
async def link_oauth(
    body: OAuthLinkRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    """用户已用 email/password 登录后,可额外绑一个 Apple/Google/微信

    注意: 不能绑已被其他用户使用的 OAuth
    """
    if body.provider == OAuthProvider.APPLE:
        if not body.id_token:
            raise HTTPException(status_code=400, detail="id_token required for Apple")
        try:
            account = await oauth_service.verify_apple_id_token(body.id_token)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
    elif body.provider == OAuthProvider.GOOGLE:
        if not body.id_token:
            raise HTTPException(status_code=400, detail="id_token required for Google")
        try:
            account = await oauth_service.verify_google_id_token(body.id_token)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
    elif body.provider == OAuthProvider.WECHAT:
        if not body.code:
            raise HTTPException(status_code=400, detail="code required for WeChat")
        try:
            account = await oauth_service.wechat_exchange_code(body.code)
        except ValueError as e:
            raise HTTPException(status_code=401, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {body.provider}")

    try:
        user = await oauth_service.link_oauth_to_user(db, current_user, account)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    return UserResponse.model_validate(user)


@router.post(
    "/unlink",
    response_model=UserResponse,
    summary="解绑 OAuth(回到 local 登录)",
)
async def unlink_oauth(
    db: AsyncSession = Depends(get_async_db),
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    if current_user.oauth_provider == OAuthProvider.LOCAL:
        raise HTTPException(
            status_code=400,
            detail="No OAuth account linked",
        )
    if not current_user.password_hash:
        raise HTTPException(
            status_code=400,
            detail="Cannot unlink: no password set. Please set a password first.",
        )
    current_user.oauth_provider = OAuthProvider.LOCAL
    current_user.oauth_id = None
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)
