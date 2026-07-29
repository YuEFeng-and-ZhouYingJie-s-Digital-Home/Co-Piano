"""
Curriculum API tests
=====================

GET /api/v1/curriculum
GET /api/v1/curriculum/{day_num}
POST /api/v1/curriculum/blocks/{id}/complete
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from main import app


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


def _signup(client, email="cur_user@example.com", password="password1", age=None):
    payload = {"email": email, "password": password}
    if age is not None:
        payload["age"] = age
    r = client.post("/api/v1/auth/signup", json=payload)
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


# ──────────────────────────────────────────────
# GET /api/v1/curriculum
# ──────────────────────────────────────────────
def test_get_curriculum_success(client):
    """首次注册即获取 7 天课程"""
    token = _signup(client)
    r = client.get(
        "/api/v1/curriculum",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert "week_id" in data
    assert data["total_days"] == 7
    assert data["total_blocks"] > 0
    # 每天都有 blocks
    for day in data["days"]:
        assert 1 <= day["day_num"] <= 7
        assert day["difficulty"] in ("beginner", "elementary", "intermediate", "advanced")
        assert len(day["blocks"]) > 0
        for block in day["blocks"]:
            assert "id" in block
            assert "type" in block
            assert "title" in block
            assert block["duration_min"] > 0


def test_get_curriculum_requires_auth(client):
    """无 token → 401/403"""
    r = client.get("/api/v1/curriculum")
    assert r.status_code in (401, 403)


def test_get_curriculum_senior_age_60(client):
    """60+ 用户 → 课程可正常生成(不报错)"""
    token = _signup(client, email="senior@example.com", age=65)
    r = client.get(
        "/api/v1/curriculum",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    # 7 天都在
    assert r.json()["total_days"] == 7


# ──────────────────────────────────────────────
# GET /api/v1/curriculum/{day_num}
# ──────────────────────────────────────────────
def test_get_curriculum_day_1(client):
    """day_num=1 → 第一天详情"""
    token = _signup(client, email="day1@example.com")
    r = client.get(
        "/api/v1/curriculum/1",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["day_num"] == 1
    assert len(data["blocks"]) > 0


def test_get_curriculum_day_7(client):
    """day_num=7 → 最后一天"""
    token = _signup(client, email="day7@example.com")
    r = client.get(
        "/api/v1/curriculum/7",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["day_num"] == 7


def test_get_curriculum_day_invalid(client):
    """day_num 越界 → 400"""
    token = _signup(client, email="dinv@example.com")
    r = client.get(
        "/api/v1/curriculum/0",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    r2 = client.get(
        "/api/v1/curriculum/8",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 400


# ──────────────────────────────────────────────
# POST /api/v1/curriculum/blocks/{id}/complete
# ──────────────────────────────────────────────
def test_mark_block_complete_success(client):
    """标记 block 完成 → 201 + SM-2 响应"""
    token = _signup(client, email="mark1@example.com")

    # 先拿一个真实 block_id
    plan = client.get(
        "/api/v1/curriculum",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    first_block_id = plan["days"][0]["blocks"][0]["id"]

    r = client.post(
        f"/api/v1/curriculum/blocks/{first_block_id}/complete",
        json={"score": 0.85, "duration_seconds": 300},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["block_id"] == first_block_id
    assert data["score"] == 0.85
    assert data["next_review_days"] > 0
    assert data["ease_factor"] >= 1.0


def test_mark_block_complete_invalid_id(client):
    """block_id 格式错误 → 400"""
    token = _signup(client, email="inv1@example.com")
    r = client.post(
        "/api/v1/curriculum/blocks/invalid_id/complete",
        json={"score": 0.5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


def test_mark_block_complete_score_range(client):
    """score 越界 → 422"""
    token = _signup(client, email="sr@example.com")
    plan = client.get(
        "/api/v1/curriculum",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    block_id = plan["days"][0]["blocks"][0]["id"]

    # score > 1
    r = client.post(
        f"/api/v1/curriculum/blocks/{block_id}/complete",
        json={"score": 1.5},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


def test_mark_block_complete_idempotent(client):
    """同 block 重复完成 → 更新不报错"""
    token = _signup(client, email="idem@example.com")
    plan = client.get(
        "/api/v1/curriculum",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    block_id = plan["days"][0]["blocks"][0]["id"]

    # 第一次
    r1 = client.post(
        f"/api/v1/curriculum/blocks/{block_id}/complete",
        json={"score": 0.7},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200

    # 第二次(同 block)
    r2 = client.post(
        f"/api/v1/curriculum/blocks/{block_id}/complete",
        json={"score": 0.9},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    # 分数应该更新
    assert r2.json()["score"] == 0.9


def test_mark_block_complete_requires_auth(client):
    """无 token → 401/403"""
    r = client.post(
        "/api/v1/curriculum/blocks/warmup_pitch_1_0/complete",
        json={"score": 0.5},
    )
    assert r.status_code in (401, 403)


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
