"""
OAuth Service — Apple / Google / WeChat 登录
============================================

策略:
- Apple: 验签 identity_token (JWT, 拿 Apple JWKS 公钥)
- Google: 验签 id_token (JWT, 拿 Google JWKS 公钥)
- WeChat: OAuth2 code → access_token → userinfo

所有 provider 统一返回 OAuthAccountInfo,业务层统一处理 upsert user

参考:
- Apple: https://developer.apple.com/documentation/sign_in_with_apple/sign_in_with_apple_rest_api
- Google: https://developers.google.com/identity/sign-in/web/backend-auth
- WeChat: https://developers.weixin.qq.com/doc/oplatform/Website_App/WeChat_Login/Wechat_Login.html
"""
from __future__ import annotations

import logging
from urllib.parse import urlencode

import httpx
import jwt
from jwt import PyJWKClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import OAuthProvider, User
from app.schemas.oauth import OAuthAccountInfo

logger = logging.getLogger("copiano.oauth")


# ──────────────────────────────────────────────
# Apple
# ──────────────────────────────────────────────
APPLE_JWKS_URL = "https://appleid.apple.com/auth/keys"
APPLE_ISSUER = "https://appleid.apple.com"


async def verify_apple_id_token(id_token: str, expected_nonce: str | None = None) -> OAuthAccountInfo:
    """验签 Apple identity token

    Apple 流程:
    1. 从 Apple JWKS 拿公钥
    2. 验证 JWT 签名
    3. 验证 iss / aud / exp
    4. 提取 sub (user_id) / email
    """
    try:
        # 1. 拿 Apple 公钥
        jwks_client = PyJWKClient(APPLE_JWKS_URL, cache_keys=True)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token).key

        # 2. 解码并验签
        # audience 应为 client_id (Bundle ID 或 Service ID)
        audience = settings.apple_client_id or "com.copiano.web"
        payload = jwt.decode(
            id_token,
            signing_key,
            algorithms=["RS256"],
            audience=audience,
            issuer=APPLE_ISSUER,
        )

        # 3. 可选 nonce 校验
        if expected_nonce and payload.get("nonce") != expected_nonce:
            raise ValueError("Nonce mismatch")

        # 4. 提取信息
        return OAuthAccountInfo(
            provider=OAuthProvider.APPLE,
            provider_user_id=payload["sub"],
            email=payload.get("email"),
            name=None,  # Apple 只在首次登录时返回 name
            avatar_url=None,
        )
    except jwt.PyJWTError as e:
        logger.warning("Apple token verification failed: %s", e)
        raise ValueError(f"Invalid Apple ID token: {e}")


# ──────────────────────────────────────────────
# Google
# ──────────────────────────────────────────────
GOOGLE_JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = {"https://accounts.google.com", "accounts.google.com"}
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


async def verify_google_id_token(id_token: str) -> OAuthAccountInfo:
    """验签 Google ID token

    方法 1 (推荐): 用 google-auth 库或 PyJWT + Google JWKS
    方法 2 (fallback): 用 tokeninfo endpoint (但需要网络)

    这里用方法 1 (PyJWT + JWKS)
    """
    try:
        jwks_client = PyJWKClient(GOOGLE_JWKS_URL, cache_keys=True)
        signing_key = jwks_client.get_signing_key_from_jwt(id_token).key

        # audience 应为 client_id (OAuth 2.0 Client ID)
        audience = settings.google_client_id or None
        decode_options = {"verify_aud": audience is not None}

        payload = jwt.decode(
            id_token,
            signing_key,
            algorithms=["RS256"],
            audience=audience,
            issuer=GOOGLE_ISSUERS,
            options=decode_options,
        )

        return OAuthAccountInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id=payload["sub"],
            email=payload.get("email"),
            name=payload.get("name"),
            avatar_url=payload.get("picture"),
        )
    except jwt.PyJWTError as e:
        logger.warning("Google token verification failed: %s", e)
        raise ValueError(f"Invalid Google ID token: {e}")


# ──────────────────────────────────────────────
# WeChat (微信)
# ──────────────────────────────────────────────
WECHAT_ACCESS_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"
WECHAT_REFRESH_URL = "https://api.weixin.qq.com/sns/oauth2/refresh_token"


async def wechat_exchange_code(code: str) -> OAuthAccountInfo:
    """微信 OAuth2 code → user info

    流程:
    1. code → access_token + openid + unionid
    2. access_token + openid → userinfo
    """
    if not settings.wechat_app_id or not settings.wechat_app_secret:
        raise ValueError("WeChat credentials not configured")

    # Step 1: code → access_token
    params = {
        "appid": settings.wechat_app_id,
        "secret": settings.wechat_app_secret,
        "code": code,
        "grant_type": "authorization_code",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(WECHAT_ACCESS_TOKEN_URL, params=params)
        data = r.json()

    if "errcode" in data and data["errcode"] != 0:
        logger.warning("WeChat code exchange failed: %s", data)
        raise ValueError(f"WeChat code exchange failed: {data.get('errmsg')}")

    access_token = data["access_token"]
    openid = data["openid"]
    unionid = data.get("unionid")  # 跨应用唯一 ID,优先用这个

    # Step 2: access_token + openid → userinfo
    info_params = {
        "access_token": access_token,
        "openid": openid,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(WECHAT_USERINFO_URL, params=info_params)
        userinfo = r.json()

    if "errcode" in userinfo and userinfo["errcode"] != 0:
        logger.warning("WeChat userinfo failed: %s", userinfo)
        raise ValueError(f"WeChat userinfo failed: {userinfo.get('errmsg')}")

    return OAuthAccountInfo(
        provider=OAuthProvider.WECHAT,
        provider_user_id=unionid or openid,  # unionid 优先
        email=None,  # 微信不返回 email
        name=userinfo.get("nickname"),
        avatar_url=userinfo.get("headimgurl"),
    )


def build_wechat_authorize_url(
    redirect_uri: str,
    state: str | None = None,
    scope: str = "snsapi_login",
) -> str:
    """构造微信扫码登录 URL

    用户扫码后会 redirect 到 redirect_uri?code=...&state=...
    """
    if not settings.wechat_app_id:
        raise ValueError("WeChat app_id not configured")

    params = {
        "appid": settings.wechat_app_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
    }
    if state:
        params["state"] = state
    return f"https://open.weixin.qq.com/connect/qrconnect?{urlencode(params)}#wechat_redirect"


# ──────────────────────────────────────────────
# 业务层:upsert user
# ──────────────────────────────────────────────
async def get_or_create_oauth_user(
    db: AsyncSession,
    account: OAuthAccountInfo,
) -> User:
    """根据 OAuth 账户信息查找或创建用户

    逻辑:
    1. 优先按 (provider, oauth_id) 查找 — 已绑定过
    2. 如果 email 存在,尝试合并到已有账户(关联登录)
    3. 否则创建新用户
    """
    # 1. 按 provider + oauth_id 找
    result = await db.execute(
        select(User).where(
            User.oauth_provider == account.provider,
            User.oauth_id == account.provider_user_id,
        )
    )
    user = result.scalar_one_or_none()
    if user:
        # 更新最后登录时间
        from datetime import datetime, timezone
        user.last_login_at = datetime.now(timezone.utc)
        await db.commit()
        return user

    # 2. 尝试按 email 合并(Apple/Google)
    if account.email:
        result = await db.execute(
            select(User).where(User.email == account.email.lower())
        )
        user = result.scalar_one_or_none()
        if user:
            # 关联到已有账户
            user.oauth_provider = account.provider
            user.oauth_id = account.provider_user_id
            from datetime import datetime, timezone
            user.last_login_at = datetime.now(timezone.utc)
            await db.commit()
            return user

    # 3. 创建新用户
    email = account.email or f"{account.provider.value}_{account.provider_user_id}@oauth.copiano.com"
    user = User(
        email=email.lower(),
        password_hash=None,  # OAuth 用户无密码
        name=account.name,
        oauth_provider=account.provider,
        oauth_id=account.provider_user_id,
        is_verified=True,  # OAuth 算已验证
    )
    if user.should_auto_senior():
        user.is_senior = True
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def link_oauth_to_user(
    db: AsyncSession,
    user: User,
    account: OAuthAccountInfo,
) -> User:
    """把 OAuth 账户绑到已登录用户

    失败: 该 OAuth 账户已被其他用户绑定
    """
    # 检查是否已被其他用户绑定
    result = await db.execute(
        select(User).where(
            User.oauth_provider == account.provider,
            User.oauth_id == account.provider_user_id,
        )
    )
    existing = result.scalar_one_or_none()
    if existing and existing.id != user.id:
        raise ValueError(
            f"This {account.provider.value} account is already linked to another user"
        )

    user.oauth_provider = account.provider
    user.oauth_id = account.provider_user_id
    await db.commit()
    await db.refresh(user)
    return user
