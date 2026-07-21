"""
Sight Reading API tests
=========================
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


def _signup(client, email="sr@example.com", password="password1"):
    r = client.post("/api/v1/auth/signup", json={
        "email": email, "password": password,
    })
    return r.json()["access_token"]


# ──────────────────────────────────────────────
# POST /sight-reading/session
# ──────────────────────────────────────────────
def test_start_session_success(client):
    """开新会话,返回第一题"""
    token = _signup(client, "start1@example.com")
    r = client.post(
        "/api/v1/sight-reading/session",
        json={"difficulty": "beginner", "mode": "random", "input_method": "keyboard"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "session_id" in data
    assert data["difficulty"] == "beginner"
    assert data["mode"] == "random"
    assert data["question_count"] == 0
    q = data["current_question"]
    assert q["method"] == "landmark"
    assert len(q["notes"]) > 0
    assert len(q["note_names"]) == len(q["notes"])


def test_start_session_4_difficulties(client):
    """4 难度都能开"""
    token = _signup(client, "sd@example.com")
    for diff in ["beginner", "elementary", "intermediate", "advanced"]:
        r = client.post(
            "/api/v1/sight-reading/session",
            json={"difficulty": diff, "mode": "random"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        assert r.json()["difficulty"] == diff


def test_start_session_3_modes(client):
    """3 模式 + 教学法对应"""
    token = _signup(client, "sm@example.com")
    expected = {"random": "landmark", "interval": "interval", "piece": "pattern"}
    for mode, method in expected.items():
        r = client.post(
            "/api/v1/sight-reading/session",
            json={"difficulty": "beginner", "mode": mode},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        assert r.json()["current_question"]["method"] == method


def test_start_session_requires_auth(client):
    """无 token → 401/403"""
    r = client.post("/api/v1/sight-reading/session", json={})
    assert r.status_code in (401, 403)


def test_start_session_invalid_difficulty(client):
    """无效难度 → 422"""
    token = _signup(client, "id@example.com")
    r = client.post(
        "/api/v1/sight-reading/session",
        json={"difficulty": "expert"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


# ──────────────────────────────────────────────
# POST /sight-reading/session/{id}/answer
# ──────────────────────────────────────────────
def test_answer_correct(client):
    """答对 → correct=True,accuracy=1.0"""
    token = _signup(client, "ac@example.com")
    r1 = client.post(
        "/api/v1/sight-reading/session",
        json={"difficulty": "beginner", "mode": "random"},
        headers={"Authorization": f"Bearer {token}"},
    )
    sid = r1.json()["session_id"]
    correct_notes = r1.json()["current_question"]["notes"]

    r2 = client.post(
        f"/api/v1/sight-reading/session/{sid}/answer",
        json={"user_notes": correct_notes},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["correct"] is True
    assert data["accuracy"] == 1.0
    assert data["matched"] == data["total"]


def test_answer_wrong(client):
    """答错 → correct=False"""
    token = _signup(client, "aw@example.com")
    r1 = client.post(
        "/api/v1/sight-reading/session",
        json={"difficulty": "beginner", "mode": "random"},
        headers={"Authorization": f"Bearer {token}"},
    )
    sid = r1.json()["session_id"]

    r2 = client.post(
        f"/api/v1/sight-reading/session/{sid}/answer",
        json={"user_notes": [60, 62, 64]},  # 瞎答
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["correct"] is False
    assert r2.json()["accuracy"] < 1.0
    # 应该有下一题
    assert r2.json()["next_question"] is not None


def test_answer_next_question_provided(client):
    """答完一题 → 下一题非空(未达 20 题上限)"""
    token = _signup(client, "anq@example.com")
    r1 = client.post(
        "/api/v1/sight-reading/session",
        json={"difficulty": "beginner", "mode": "random"},
        headers={"Authorization": f"Bearer {token}"},
    )
    sid = r1.json()["session_id"]
    client.post(
        f"/api/v1/sight-reading/session/{sid}/answer",
        json={"user_notes": [60, 62, 64, 65, 67]},
        headers={"Authorization": f"Bearer {token}"},
    )
    # 第二次答题
    r2 = client.post(
        f"/api/v1/sight-reading/session/{sid}/answer",
        json={"user_notes": [60, 62, 64, 65, 67]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.json()["next_question"] is not None
    assert r2.json()["session_complete"] is False


def test_answer_session_not_found(client):
    """不存在 session → 404"""
    token = _signup(client, "ns@example.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.post(
        f"/api/v1/sight-reading/session/{fake_id}/answer",
        json={"user_notes": [60]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


def test_answer_other_user_forbidden(client):
    """别人的 session → 403"""
    token_a = _signup(client, "osa@example.com")
    token_b = _signup(client, "osb@example.com")
    r1 = client.post(
        "/api/v1/sight-reading/session",
        json={"difficulty": "beginner", "mode": "random"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    sid = r1.json()["session_id"]
    r2 = client.post(
        f"/api/v1/sight-reading/session/{sid}/answer",
        json={"user_notes": [60]},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r2.status_code == 403


# ──────────────────────────────────────────────
# GET /sight-reading/session/{id}
# ──────────────────────────────────────────────
def test_get_session_detail(client):
    """会话详情"""
    token = _signup(client, "gd@example.com")
    r1 = client.post(
        "/api/v1/sight-reading/session",
        json={"difficulty": "beginner", "mode": "random"},
        headers={"Authorization": f"Bearer {token}"},
    )
    sid = r1.json()["session_id"]
    # 答 2 题
    client.post(
        f"/api/v1/sight-reading/session/{sid}/answer",
        json={"user_notes": [60, 62, 64, 65, 67]},
        headers={"Authorization": f"Bearer {token}"},
    )
    client.post(
        f"/api/v1/sight-reading/session/{sid}/answer",
        json={"user_notes": [60, 62, 64, 65, 67]},
        headers={"Authorization": f"Bearer {token}"},
    )

    r3 = client.get(
        f"/api/v1/sight-reading/session/{sid}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r3.status_code == 200
    data = r3.json()
    assert data["session_id"] == sid
    assert data["stats"]["total_questions"] == 2
    assert "accuracy" in data["stats"]


def test_get_session_other_user_forbidden(client):
    """别人的 session → 403"""
    token_a = _signup(client, "gsa@example.com")
    token_b = _signup(client, "gsb@example.com")
    r1 = client.post(
        "/api/v1/sight-reading/session",
        json={"difficulty": "beginner", "mode": "random"},
        headers={"Authorization": f"Bearer {token_a}"},
    )
    sid = r1.json()["session_id"]
    r2 = client.get(
        f"/api/v1/sight-reading/session/{sid}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r2.status_code == 403


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
