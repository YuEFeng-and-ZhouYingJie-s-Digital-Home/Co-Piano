"""
Feedback API tests — LLM 教学反馈
====================================

Mock llm_service.generate_feedback 避免真实 LLM 调用
"""
import io
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import mido
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.services.llm_service import LLMResponse
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


def _create_midi_bytes(pitches):
    buf = io.BytesIO()
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120), time=0))
    beat = int(mido.second2tick(60.0/120, mid.ticks_per_beat, mido.bpm2tempo(120)))
    for p in pitches:
        track.append(mido.Message('note_on', note=p, velocity=64, time=0))
        track.append(mido.Message('note_off', note=p, velocity=64, time=beat))
    mid.save(file=buf)
    buf.seek(0)
    return buf


def _signup(client, email, password="password1"):
    r = client.post("/api/v1/auth/signup", json={"email": email, "password": password})
    return r.json()["access_token"]


def _create_evaluation(client, token, piece="Test Piece"):
    """创建评估(返回 evaluation_id)"""
    midi = _create_midi_bytes([60, 62, 64, 65, 67])
    r = client.post(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token}"},
        data={"piece_name": piece, "difficulty": "elementary"},
        files={"midi_file": ("x.mid", midi, "audio/midi")},
    )
    assert r.status_code == 201
    return r.json()["evaluation"]["id"]


def _mock_llm_feedback(content="Mocked LLM feedback", backend="qwen", latency=200):
    """Mock llm_service.generate_feedback"""
    async def fake(*args, **kwargs):
        return LLMResponse(
            content=content,
            model="qwen2.5-7b-instruct",
            backend=backend,
            latency_ms=latency,
            prompt_tokens=50,
            completion_tokens=30,
            total_tokens=80,
        )
    return fake


# ──────────────────────────────────────────────
# POST /api/v1/feedback
# ──────────────────────────────────────────────
def test_create_feedback_success(client):
    """创建反馈 → 200 + 内容 + 回写 PG"""
    token = _signup(client, "fb1@example.com")
    eval_id = _create_evaluation(client, token, "Bach Prelude")

    with patch(
        "app.api.v1.feedback.llm_service.generate_feedback",
        new=AsyncMock(side_effect=_mock_llm_feedback("很好,音准不错")),
    ):
        r = client.post(
            "/api/v1/feedback",
            json={"evaluation_id": eval_id},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["evaluation_id"] == eval_id
    assert data["feedback"] == "很好,音准不错"
    assert data["backend"] == "qwen"
    assert data["latency_ms"] == 200
    assert data["total_tokens"] == 80


def test_create_feedback_persisted_to_pg(client):
    """调完 LLM 后,evaluation.llm_feedback 写回 PG"""
    token = _signup(client, "fb2@example.com")
    eval_id = _create_evaluation(client, token)

    with patch(
        "app.api.v1.feedback.llm_service.generate_feedback",
        new=AsyncMock(side_effect=_mock_llm_feedback("持久化测试反馈")),
    ):
        r = client.post(
            "/api/v1/feedback",
            json={"evaluation_id": eval_id},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 200

    # 再查 evaluation 详情,应该看到 llm_feedback
    r2 = client.get(
        f"/api/v1/evaluations/{eval_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.json()["llm_feedback"] == "持久化测试反馈"
    assert r2.json()["llm_latency_ms"] == 200


def test_create_feedback_not_found(client):
    """评估不存在 → 404"""
    token = _signup(client, "fb3@example.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.post(
        "/api/v1/feedback",
        json={"evaluation_id": fake_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


def test_create_feedback_other_user_forbidden(client):
    """别人的评估 → 403"""
    token_a = _signup(client, "fba@example.com")
    token_b = _signup(client, "fbb@example.com")
    eval_id = _create_evaluation(client, token_a)

    r = client.post(
        "/api/v1/feedback",
        json={"evaluation_id": eval_id},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 403


def test_create_feedback_llm_unavailable(client):
    """LLM 全失败 → 503"""
    token = _signup(client, "fb4@example.com")
    eval_id = _create_evaluation(client, token)

    with patch(
        "app.api.v1.feedback.llm_service.generate_feedback",
        new=AsyncMock(side_effect=RuntimeError("All LLM backends failed")),
    ):
        r = client.post(
            "/api/v1/feedback",
            json={"evaluation_id": eval_id},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert r.status_code == 503
    assert "LLM service unavailable" in r.json()["detail"]


def test_create_feedback_requires_auth(client):
    """无 token → 401/403"""
    r = client.post(
        "/api/v1/feedback",
        json={"evaluation_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert r.status_code in (401, 403)


# ──────────────────────────────────────────────
# GET /api/v1/feedback/{evaluation_id}
# ──────────────────────────────────────────────
def test_get_feedback_after_create(client):
    """生成后能 GET 回"""
    token = _signup(client, "fb5@example.com")
    eval_id = _create_evaluation(client, token)

    with patch(
        "app.api.v1.feedback.llm_service.generate_feedback",
        new=AsyncMock(side_effect=_mock_llm_feedback("GET 测试反馈")),
    ):
        client.post(
            "/api/v1/feedback",
            json={"evaluation_id": eval_id},
            headers={"Authorization": f"Bearer {token}"},
        )

    r = client.get(
        f"/api/v1/feedback/{eval_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["feedback"] == "GET 测试反馈"


def test_get_feedback_not_generated(client):
    """未生成反馈 → 404"""
    token = _signup(client, "fb6@example.com")
    eval_id = _create_evaluation(client, token)
    # 不调 POST,直接 GET
    r = client.get(
        f"/api/v1/feedback/{eval_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert "No feedback generated" in r.json()["detail"]


def test_get_feedback_invalid_id(client):
    """evaluation_id 不是 UUID → 400"""
    token = _signup(client, "fb7@example.com")
    r = client.get(
        "/api/v1/feedback/not-a-uuid",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400


# ──────────────────────────────────────────────
# GET /api/v1/feedback/history
# ──────────────────────────────────────────────
def test_history_empty(client):
    """无反馈 → 空"""
    token = _signup(client, "fb8@example.com")
    r = client.get(
        "/api/v1/feedback/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0


def test_history_pagination(client):
    """3 个反馈,limit 2 → 2 + 1"""
    token = _signup(client, "fb9@example.com")

    # 创建 3 个评估 + 反馈
    eval_ids = []
    for i in range(3):
        eid = _create_evaluation(client, token, f"Piece {i}")
        eval_ids.append(eid)

    with patch(
        "app.api.v1.feedback.llm_service.generate_feedback",
        new=AsyncMock(side_effect=_mock_llm_feedback(f"反馈 {i}")),
    ):
        for eid in eval_ids:
            client.post(
                "/api/v1/feedback",
                json={"evaluation_id": eid},
                headers={"Authorization": f"Bearer {token}"},
            )

    # 查 history
    r = client.get(
        "/api/v1/feedback/history?limit=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 3
    assert len(data["items"]) == 2
    # 每项有 preview
    for item in data["items"]:
        assert "feedback_preview" in item
        assert "evaluation_id" in item
        assert "model" in item


def test_history_only_feedback_with_llm(client):
    """只列有 LLM 反馈的评估"""
    token = _signup(client, "fb10@example.com")
    # 2 个评估:1 个有反馈,1 个无
    eid1 = _create_evaluation(client, token, "With Feedback")
    _create_evaluation(client, token, "No Feedback")

    with patch(
        "app.api.v1.feedback.llm_service.generate_feedback",
        new=AsyncMock(side_effect=_mock_llm_feedback("only me")),
    ):
        client.post(
            "/api/v1/feedback",
            json={"evaluation_id": eid1},
            headers={"Authorization": f"Bearer {token}"},
        )

    r = client.get(
        "/api/v1/feedback/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.json()["total"] == 1  # 只 1 个有反馈


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
