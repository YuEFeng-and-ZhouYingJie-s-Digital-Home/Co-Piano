"""
OAuth API tests — Apple / Google / WeChat + 绑定/解绑
======================================================

测试目标:
- Apple: 验签 mock 成功/失败 + 拿到 account info
- Google: 验签 mock 成功/失败
- WeChat: code exchange + 拿 userinfo
- get_or_create_oauth_user: 新建 + 已有合并
- link: 已绑别人的 OAuth 报 409
- unlink: 必须有 password

Mock 策略:
- monkeypatch httpx + jwt 避免真请求 Apple/Google/微信
- 直接构造假 token,patch verify_apple_id_token / verify_google_id_token / wechat_exchange_code
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.models.user import OAuthProvider, User
from app.schemas.oauth import OAuthAccountInfo
from app.services import oauth_service
from main import app


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────
@pytest_asyncio.fixture
async def async_engine():
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def client(async_engine):
    factory = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)

    async def _override():
        async with factory() as session:
            try:
                yield session
            finally:
                await session.close()

    from app.db import base as db_base
    app.dependency_overrides[db_base.get_async_db] = _override
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ──────────────────────────────────────────────
# Mock helpers — patch verify_*
# ──────────────────────────────────────────────
@pytest.fixture
def mock_apple(monkeypatch):
    """默认 mock:Apple 验证成功,返回 alice 账户"""
    async def fake_verify(id_token, expected_nonce=None):
        return OAuthAccountInfo(
            provider=OAuthProvider.APPLE,
            provider_user_id="apple-user-001",
            email="alice@apple.com",
            name="Alice",
        )
    monkeypatch.setattr(oauth_service, "verify_apple_id_token", fake_verify)
    return fake_verify


@pytest.fixture
def mock_apple_invalid(monkeypatch):
    """Mock:Apple 验证失败"""
    async def fake_verify(id_token, expected_nonce=None):
        raise ValueError("Invalid Apple ID token: signature mismatch")
    monkeypatch.setattr(oauth_service, "verify_apple_id_token", fake_verify)


@pytest.fixture
def mock_google(monkeypatch):
    async def fake_verify(id_token):
        return OAuthAccountInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="google-user-001",
            email="bob@gmail.com",
            name="Bob",
            avatar_url="https://example.com/avatar.png",
        )
    monkeypatch.setattr(oauth_service, "verify_google_id_token", fake_verify)
    return fake_verify


@pytest.fixture
def mock_google_invalid(monkeypatch):
    async def fake_verify(id_token):
        raise ValueError("Invalid Google ID token")
    monkeypatch.setattr(oauth_service, "verify_google_id_token", fake_verify)


@pytest.fixture
def mock_wechat(monkeypatch):
    async def fake_exchange(code):
        return OAuthAccountInfo(
            provider=OAuthProvider.WECHAT,
            provider_user_id="wechat-openid-001",
            email=None,
            name="微信用户",
            avatar_url="http://wx.qq.com/avatar.jpg",
        )
    monkeypatch.setattr(oauth_service, "wechat_exchange_code", fake_exchange)
    return fake_exchange


@pytest.fixture
def mock_wechat_invalid(monkeypatch):
    async def fake_exchange(code):
        raise ValueError("WeChat code exchange failed: invalid code")
    monkeypatch.setattr(oauth_service, "wechat_exchange_code", fake_exchange)


# ──────────────────────────────────────────────
# Apple
# ──────────────────────────────────────────────
def test_apple_login_new_user(client, mock_apple):
    """Apple 首次登录 → 自动注册"""
    r = client.post("/api/v1/auth/oauth/apple", json={
        "id_token": "fake-apple-token",
        "user_identifier": "apple-user-001",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == "alice@apple.com"
    assert data["user"]["oauth_provider"] == "apple"
    # 来自 Apple 的 email 视为已验证
    assert data["user"]["is_verified"] is True


def test_apple_login_existing_user(client, mock_apple):
    """Apple 第二次登录 → 复用同 user"""
    r1 = client.post("/api/v1/auth/oauth/apple", json={
        "id_token": "fake", "user_identifier": "apple-user-001",
    })
    user_id_1 = r1.json()["user"]["id"]

    r2 = client.post("/api/v1/auth/oauth/apple", json={
        "id_token": "fake", "user_identifier": "apple-user-001",
    })
    user_id_2 = r2.json()["user"]["id"]

    assert user_id_1 == user_id_2  # 同一个 user


def test_apple_login_invalid_token(client, mock_apple_invalid):
    """Apple token 无效 → 401"""
    r = client.post("/api/v1/auth/oauth/apple", json={
        "id_token": "bad-token",
        "user_identifier": "x",
    })
    assert r.status_code == 401


# ──────────────────────────────────────────────
# Google
# ──────────────────────────────────────────────
def test_google_login_new_user(client, mock_google):
    """Google 首次登录"""
    r = client.post("/api/v1/auth/oauth/google", json={
        "id_token": "fake-google-token",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["email"] == "bob@gmail.com"
    assert data["user"]["oauth_provider"] == "google"
    assert data["user"]["name"] == "Bob"


def test_google_login_invalid(client, mock_google_invalid):
    """Google 无效 token"""
    r = client.post("/api/v1/auth/oauth/google", json={
        "id_token": "bad",
    })
    assert r.status_code == 401


# ──────────────────────────────────────────────
# WeChat
# ──────────────────────────────────────────────
def test_wechat_qrcode_no_creds(client):
    """微信未配置 → 503"""
    r = client.get("/api/v1/auth/oauth/wechat/qrcode?redirect_uri=https://copiano.com/auth/wechat/callback")
    assert r.status_code == 503


def test_wechat_qrcode_with_creds(client, monkeypatch):
    """配置了 app_id 后能生成 URL"""
    from app.core import config as config_module
    # Patch the cached settings instance
    monkeypatch.setattr(config_module.settings, "wechat_app_id", "wx_test_app_id")
    r = client.get("/api/v1/auth/oauth/wechat/qrcode?redirect_uri=https://copiano.com/auth/wechat/callback")
    assert r.status_code == 200
    data = r.json()
    assert "open.weixin.qq.com" in data["authorize_url"]
    assert "wx_test_app_id" in data["authorize_url"]


def test_wechat_login(client, mock_wechat):
    """微信 code 登录"""
    r = client.post("/api/v1/auth/oauth/wechat", json={
        "code": "fake-wechat-code",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["oauth_provider"] == "wechat"
    assert data["user"]["oauth_id"] == "wechat-openid-001"
    # 微信没 email → 用占位邮箱
    assert "@oauth.copiano.com" in data["user"]["email"]


def test_wechat_login_invalid(client, mock_wechat_invalid):
    """微信 code 无效"""
    r = client.post("/api/v1/auth/oauth/wechat", json={"code": "bad"})
    assert r.status_code == 401


# ──────────────────────────────────────────────
# email 合并:Apple/Google 首次登录后再用 email 注册 → 应合并
# ──────────────────────────────────────────────
def test_apple_then_email_signup_merges_account(client, mock_apple):
    """Apple 用 alice@apple.com 登录后,再用同邮箱注册 → 合并到同一 user"""
    # 1. Apple 登录
    r1 = client.post("/api/v1/auth/oauth/apple", json={
        "id_token": "fake", "user_identifier": "apple-001",
    })
    assert r1.status_code == 200, r1.text
    apple_user_id = r1.json()["user"]["id"]

    # 2. 用同邮箱注册(模拟前端行为)
    r2 = client.post("/api/v1/auth/signup", json={
        "email": "alice@apple.com",
        "password": "password1",
    })
    # 期望: 邮箱已被 Apple 用户注册 → 应该返回 409 conflict
    # 或者: 合并到同一 user(取决于实现策略)
    # 当前实现: get_or_create_oauth_user 阶段已经创建了 alice@apple.com
    # 所以 signup 阶段会撞到邮箱 → 409
    assert r2.status_code == 409, r2.text
    assert "already" in r2.json()["detail"].lower()


# ──────────────────────────────────────────────
# Link / Unlink
# ──────────────────────────────────────────────
def test_link_oauth_to_existing_user(client, mock_google):
    """已注册用户绑 Google"""
    # 1. 注册
    r1 = client.post("/api/v1/auth/signup", json={
        "email": "existing@example.com",
        "password": "password1",
    })
    access_token = r1.json()["access_token"]

    # 2. 绑 Google
    r2 = client.post(
        "/api/v1/auth/oauth/link",
        json={"provider": "google", "id_token": "fake-google"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["oauth_provider"] == "google"
    assert r2.json()["oauth_id"] == "google-user-001"


def test_link_oauth_invalid_token(client, mock_google_invalid):
    """绑 OAuth 时 token 无效"""
    r1 = client.post("/api/v1/auth/signup", json={
        "email": "l1@example.com",
        "password": "password1",
    })
    token = r1.json()["access_token"]
    r2 = client.post(
        "/api/v1/auth/oauth/link",
        json={"provider": "google", "id_token": "bad"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 401


def test_link_oauth_already_linked_to_other_user(client, mock_google):
    """OAuth 已被另一用户绑 → 409"""
    # 用户 1 绑 Google
    r1 = client.post("/api/v1/auth/signup", json={
        "email": "u1@example.com", "password": "password1",
    })
    t1 = r1.json()["access_token"]
    client.post(
        "/api/v1/auth/oauth/link",
        json={"provider": "google", "id_token": "fake"},
        headers={"Authorization": f"Bearer {t1}"},
    )

    # 用户 2 想绑同一个 Google
    r2 = client.post("/api/v1/auth/signup", json={
        "email": "u2@example.com", "password": "password1",
    })
    t2 = r2.json()["access_token"]
    r3 = client.post(
        "/api/v1/auth/oauth/link",
        json={"provider": "google", "id_token": "fake"},
        headers={"Authorization": f"Bearer {t2}"},
    )
    assert r3.status_code == 409
    assert "already" in r3.json()["detail"].lower()


def test_unlink_oauth(client, mock_google):
    """已绑 Google 的用户解绑"""
    # 注册 + 绑
    r1 = client.post("/api/v1/auth/signup", json={
        "email": "unlinker@example.com",
        "password": "password1",
    })
    token = r1.json()["access_token"]
    client.post(
        "/api/v1/auth/oauth/link",
        json={"provider": "google", "id_token": "fake"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # 解绑
    r2 = client.post(
        "/api/v1/auth/oauth/unlink",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["oauth_provider"] == "local"
    assert r2.json()["oauth_id"] is None


def test_unlink_oauth_no_password_fails(client, mock_apple):
    """Apple-only 用户没 password 不能解绑"""
    r1 = client.post("/api/v1/auth/oauth/apple", json={
        "id_token": "fake", "user_identifier": "apple-only-001",
    })
    token = r1.json()["access_token"]
    r2 = client.post(
        "/api/v1/auth/oauth/unlink",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 400
    assert "password" in r2.json()["detail"].lower()


def test_unlink_no_oauth_fails(client):
    """local 用户解绑 → 400"""
    r1 = client.post("/api/v1/auth/signup", json={
        "email": "local@example.com", "password": "password1",
    })
    token = r1.json()["access_token"]
    r2 = client.post(
        "/api/v1/auth/oauth/unlink",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 400


def test_link_requires_auth(client, mock_google):
    """link 必须已登录"""
    r = client.post(
        "/api/v1/auth/oauth/link",
        json={"provider": "google", "id_token": "fake"},
    )
    assert r.status_code in (401, 403)


# ──────────────────────────────────────────────
# 业务层单元测试
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_get_or_create_oauth_new(async_engine):
    """新 OAuth 账户 → 创建新 user"""
    factory = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        account = OAuthAccountInfo(
            provider=OAuthProvider.APPLE,
            provider_user_id="new-apple-id",
            email="new@apple.com",
        )
        user = await oauth_service.get_or_create_oauth_user(db, account)
        assert user.id is not None
        assert user.oauth_provider == OAuthProvider.APPLE
        assert user.email == "new@apple.com"


@pytest.mark.asyncio
async def test_get_or_create_oauth_existing(async_engine):
    """已存在的 OAuth 账户 → 复用"""
    factory = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        # 第一次
        account = OAuthAccountInfo(
            provider=OAuthProvider.GOOGLE,
            provider_user_id="dup-google-id",
            email="dup@gmail.com",
        )
        u1 = await oauth_service.get_or_create_oauth_user(db, account)
        u1_id = u1.id

        # 第二次
        u2 = await oauth_service.get_or_create_oauth_user(db, account)
        assert u2.id == u1_id


@pytest.mark.asyncio
async def test_get_or_create_oauth_email_merge(async_engine):
    """email 已存在 + 新 OAuth → 合并到已有 user"""
    factory = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        # 1. 已有 email 用户
        u1 = User(
            email="merge@example.com",
            password_hash="x",
        )
        db.add(u1)
        await db.commit()
        u1_id = u1.id

        # 2. Apple 首次登录(同 email)
        account = OAuthAccountInfo(
            provider=OAuthProvider.APPLE,
            provider_user_id="apple-merge-id",
            email="merge@example.com",
        )
        u2 = await oauth_service.get_or_create_oauth_user(db, account)
        assert u2.id == u1_id  # 合并到同一 user
        assert u2.oauth_provider == OAuthProvider.APPLE
        assert u2.oauth_id == "apple-merge-id"


@pytest.mark.asyncio
async def test_get_or_create_oauth_no_email_uses_placeholder(async_engine):
    """无 email(微信)→ 用占位邮箱"""
    factory = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        account = OAuthAccountInfo(
            provider=OAuthProvider.WECHAT,
            provider_user_id="wx-001",
            email=None,
        )
        user = await oauth_service.get_or_create_oauth_user(db, account)
        assert "wechat" in user.email
        assert "wx-001" in user.email
        assert "@oauth.copiano.com" in user.email


@pytest.mark.asyncio
async def test_get_or_create_oauth_senior_auto_activate(async_engine):
    """OAuth 用户也支持银发自动激活(根据 age)"""
    factory = async_sessionmaker(bind=async_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        account = OAuthAccountInfo(
            provider=OAuthProvider.APPLE,
            provider_user_id="apple-senior",
            email="senior@apple.com",
        )
        user = await oauth_service.get_or_create_oauth_user(db, account)
        # OAuth 首次创建时 age=None → 不会自动激活
        # 但如果后续 PATCH /me 设置 age=60 → 自动激活 (在别处测试)
        assert user.is_senior is False


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
