"""
OAuth Schemas — Apple / Google / WeChat
========================================
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.models.user import OAuthProvider
from app.schemas.auth import TokenResponse


# ──────────────────────────────────────────────
# Apple Sign In
# ──────────────────────────────────────────────
class AppleCallbackRequest(BaseModel):
    """Apple identity token 回调(从前端 / iOS native)

    Apple Sign In 流程:
    - Web: redirect → /auth/apple/callback?id_token=...&user={...}
    - iOS: native ASAuthorizationAppleIDProvider → 前端拿到 identityToken → POST 给后端
    """
    id_token: str = Field(..., description="Apple identity token (JWT)")
    user_identifier: str = Field(..., description="Apple user ID (sub)")
    email: Optional[str] = None  # Apple 只在首次登录时返回
    full_name: Optional[str] = None  # 同上
    nonce: Optional[str] = None  # 用于防重放


# ──────────────────────────────────────────────
# Google Sign In
# ──────────────────────────────────────────────
class GoogleCallbackRequest(BaseModel):
    """Google ID token 回调

    Google Sign In 流程:
    - Web: Google Identity Services → 返回 ID token (JWT) → POST 给后端
    - iOS: GIDSignIn → idToken → POST 给后端
    """
    id_token: str = Field(..., description="Google ID token (JWT)")
    access_token: Optional[str] = None  # 用于后续 refresh / revoke
    # 实际从 JWT 解析得到:
    # - sub (Google user ID)
    # - email
    # - email_verified
    # - name
    # - picture


# ──────────────────────────────────────────────
# WeChat (微信扫码)
# ──────────────────────────────────────────────
class WeChatCallbackRequest(BaseModel):
    """微信 OAuth2 code 回调

    微信扫码流程:
    1. 前端生成二维码(后端 /wechat/qrcode 返回 url)
    2. 用户扫码 → 微信 redirect → /wechat/callback?code=...&state=...
    3. 后端用 code 换 access_token + openid
    4. 用 access_token + openid 拉用户信息
    """
    code: str = Field(..., description="微信 OAuth code")
    state: Optional[str] = None  # 防 CSRF


# ──────────────────────────────────────────────
# 通用
# ──────────────────────────────────────────────
class OAuthLinkRequest(BaseModel):
    """把 OAuth 账户绑到已登录用户"""
    provider: OAuthProvider
    id_token: str  # Apple / Google
    # WeChat 特殊
    code: Optional[str] = None


class OAuthAccountInfo(BaseModel):
    """OAuth 用户信息(从 provider 拿到的)"""
    provider: OAuthProvider
    provider_user_id: str
    email: Optional[str] = None
    name: Optional[str] = None
    avatar_url: Optional[str] = None
