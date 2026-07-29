"""
Auth API tests — 注册 / 登录 / 刷新 / 登出 / /me
==================================================

测试目标:
- signup: 成功 + 邮箱已存在 + 弱密码
- login: 成功 + 错误密码 + 不存在用户
- refresh: 成功 + 过期 + 错误类型 token
- logout: 成功
- /me: 需要 Bearer + 拿自己信息 + 更新资料
- 银发模式自动激活
- token 包含正确的 sub/type/exp/iss

用 aiosqlite + AsyncEngine 让 FastAPI async 端点能跑通
"""
import sys
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

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.base import Base
from main import app


# ──────────────────────────────────────────────
# Fixtures — aiosqlite 异步内存 DB
# ──────────────────────────────────────────────
@pytest_asyncio.fixture
async def async_engine():
    """异步 SQLite 内存引擎"""
    eng = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


@pytest_asyncio.fixture
async def async_session_factory(async_engine):
    """异步 session 工厂"""
    return async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


@pytest_asyncio.fixture
async def client(async_session_factory):
    """FastAPI TestClient,get_async_db 替换为测试用 session"""
    from app.db import base as db_base

    async def _override_get_async_db():
        async with async_session_factory() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[db_base.get_async_db] = _override_get_async_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ──────────────────────────────────────────────
# Unit tests — security module
# ──────────────────────────────────────────────
def test_password_hash_and_verify():
    """bcrypt 哈希 + 验证"""
    h = hash_password("mysecret123")
    assert h != "mysecret123"
    assert h.startswith("$2b$")
    assert verify_password("mysecret123", h) is True
    assert verify_password("wrong", h) is False


def test_password_hash_unique_per_call():
    """bcrypt 每次哈希不同 (salt 随机)"""
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2
    assert verify_password("same", h1) is True
    assert verify_password("same", h2) is True


def test_access_token_decode():
    """access token 可解码并包含 sub/type"""
    token = create_access_token("user-123")
    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == "user-123"
    assert payload["type"] == "access"
    assert payload["iss"] == "copiano-api"
    assert "exp" in payload
    assert "iat" in payload


def test_refresh_token_decode():
    """refresh token 解码"""
    token = create_refresh_token("user-456")
    payload = decode_token(token, expected_type="refresh")
    assert payload["sub"] == "user-456"
    assert payload["type"] == "refresh"


def test_token_type_mismatch():
    """access token 当 refresh 用会报错"""
    import jwt as pyjwt
    token = create_access_token("user-1")
    with pytest.raises(pyjwt.InvalidTokenError):
        decode_token(token, expected_type="refresh")


def test_token_with_extra_claims():
    """自定义 claims 合并"""
    token = create_access_token("user-1", extra_claims={"role": "admin", "tier": "pro"})
    payload = decode_token(token)
    assert payload["role"] == "admin"
    assert payload["tier"] == "pro"


# ──────────────────────────────────────────────
# Integration tests — /api/v1/auth/*
# ──────────────────────────────────────────────
def test_signup_success(client):
    """注册成功"""
    r = client.post("/api/v1/auth/signup", json={
        "email": "alice@example.com",
        "password": "securepass123",
        "name": "Alice",
        "age": 25,
    })
    assert r.status_code == 201, r.text
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["email"] == "alice@example.com"
    assert data["user"]["is_senior"] is False
    assert data["user"]["subscription_tier"] == "free"


def test_signup_weak_password(client):
    """密码 < 8 字符被拒"""
    r = client.post("/api/v1/auth/signup", json={
        "email": "weak@example.com",
        "password": "short",
    })
    assert r.status_code == 422  # Pydantic validation


def test_signup_duplicate_email(client):
    """重复邮箱"""
    client.post("/api/v1/auth/signup", json={
        "email": "dup@example.com",
        "password": "password1",
    })
    r = client.post("/api/v1/auth/signup", json={
        "email": "dup@example.com",
        "password": "password2",
    })
    assert r.status_code == 409
    assert "already" in r.json()["detail"].lower()


def test_signup_senior_auto_activate(client):
    """age ≥ 60 自动激活银发模式"""
    r = client.post("/api/v1/auth/signup", json={
        "email": "grandma@example.com",
        "password": "securepass123",
        "age": 65,
    })
    assert r.status_code == 201, r.text
    assert r.json()["user"]["is_senior"] is True


def test_signup_password_mismatch(client):
    """confirm_password 不一致"""
    r = client.post("/api/v1/auth/signup", json={
        "email": "mm@example.com",
        "password": "password1",
        "confirm_password": "password2",
    })
    assert r.status_code == 400


def test_login_success(client):
    """登录成功"""
    client.post("/api/v1/auth/signup", json={
        "email": "login@example.com",
        "password": "mypassword",
    })
    r = client.post("/api/v1/auth/login", json={
        "email": "login@example.com",
        "password": "mypassword",
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data["user"]["email"] == "login@example.com"


def test_login_wrong_password(client):
    """密码错误"""
    client.post("/api/v1/auth/signup", json={
        "email": "wp@example.com",
        "password": "correct",
    })
    r = client.post("/api/v1/auth/login", json={
        "email": "wp@example.com",
        "password": "wrong",
    })
    assert r.status_code == 401


def test_login_nonexistent_user(client):
    """用户不存在"""
    r = client.post("/api/v1/auth/login", json={
        "email": "ghost@example.com",
        "password": "anything",
    })
    assert r.status_code == 401


def test_refresh_success(client):
    """refresh token 换新 access"""
    signup = client.post("/api/v1/auth/signup", json={
        "email": "refresh@example.com",
        "password": "password1",
    })
    refresh_token = signup.json()["refresh_token"]
    r = client.post("/api/v1/auth/refresh", json={
        "refresh_token": refresh_token,
    })
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["access_token"] != refresh_token


def test_refresh_invalid_token(client):
    """无效 refresh token"""
    r = client.post("/api/v1/auth/refresh", json={
        "refresh_token": "this-is-not-a-jwt",
    })
    assert r.status_code == 401


def test_refresh_using_access_token_as_refresh(client):
    """用 access token 当 refresh (类型不匹配)"""
    signup = client.post("/api/v1/auth/signup", json={
        "email": "typemismatch@example.com",
        "password": "password1",
    })
    access_token = signup.json()["access_token"]
    r = client.post("/api/v1/auth/refresh", json={
        "refresh_token": access_token,
    })
    assert r.status_code == 401


def test_logout(client):
    """登出"""
    r = client.post("/api/v1/auth/logout")
    assert r.status_code == 200
    assert "logged out" in r.json()["message"].lower()


# ──────────────────────────────────────────────
# Integration tests — /api/v1/users/me
# ──────────────────────────────────────────────
def _signup_and_get_token(client, email="me@example.com", password="password1"):
    """辅助:注册并返回 (token, user_id)"""
    r = client.post("/api/v1/auth/signup", json={
        "email": email,
        "password": password,
    })
    return r.json()["access_token"], r.json()["user"]["id"]


def test_get_me_success(client):
    """GET /me 需要 Bearer"""
    token, _ = _signup_and_get_token(client)
    r = client.get("/api/v1/users/me", headers={
        "Authorization": f"Bearer {token}",
    })
    assert r.status_code == 200, r.text
    assert r.json()["email"] == "me@example.com"


def test_get_me_no_token(client):
    """缺 token 返回 403"""
    r = client.get("/api/v1/users/me")
    assert r.status_code in (401, 403)


def test_get_me_invalid_token(client):
    """无效 token 返回 401"""
    r = client.get("/api/v1/users/me", headers={
        "Authorization": "Bearer invalid-jwt-token",
    })
    assert r.status_code == 401


def test_get_me_wrong_type_token(client):
    """refresh token 不能访问 /me"""
    signup = client.post("/api/v1/auth/signup", json={
        "email": "wt@example.com",
        "password": "password1",
    })
    refresh = signup.json()["refresh_token"]
    r = client.get("/api/v1/users/me", headers={
        "Authorization": f"Bearer {refresh}",
    })
    assert r.status_code == 401


def test_update_me_age_triggers_senior(client):
    """PATCH /me age=60 自动激活银发"""
    token, _ = _signup_and_get_token(client, email="late@example.com")
    r = client.patch(
        "/api/v1/users/me?age=65",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_senior"] is True


def test_update_me_name(client):
    """PATCH /me name"""
    token, _ = _signup_and_get_token(client, email="rename@example.com")
    r = client.patch(
        "/api/v1/users/me?name=new_name",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "new_name"


def test_full_flow_signup_login_refresh_me(client):
    """完整流程:注册 → /me → refresh → /me → 错误密码登录失败"""
    import time
    # 注册
    r1 = client.post("/api/v1/auth/signup", json={
        "email": "flow@example.com",
        "password": "password1",
    })
    assert r1.status_code == 201
    access1 = r1.json()["access_token"]
    refresh1 = r1.json()["refresh_token"]

    # 用 access 拿自己
    r2 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access1}"})
    assert r2.status_code == 200

    # 等待 1 秒 (确保 iat 变化)
    time.sleep(1.1)

    # refresh 换新 access
    r3 = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh1})
    assert r3.status_code == 200
    access2 = r3.json()["access_token"]
    # 新 token 的 iat 不同,所以签名也不同
    assert access2 != access1

    # 新 access 也能用
    r4 = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access2}"})
    assert r4.status_code == 200

    # 用错误密码登录失败
    r5 = client.post("/api/v1/auth/login", json={
        "email": "flow@example.com",
        "password": "wrong",
    })
    assert r5.status_code == 401


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
