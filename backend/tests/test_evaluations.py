"""
Evaluations API tests — POST/GET/history
========================================
"""
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import io

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
from app.models.user import User
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


def _create_midi_bytes(pitches, bpm=120):
    """生成 MIDI 文件 bytes"""
    buf = io.BytesIO()
    mid = mido.MidiFile()
    track = mido.MidiTrack()
    mid.tracks.append(track)
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(bpm), time=0))
    beat = int(mido.second2tick(60.0 / bpm, mid.ticks_per_beat, mido.bpm2tempo(bpm)))
    for p in pitches:
        track.append(mido.Message('note_on', note=p, velocity=64, time=0))
        track.append(mido.Message('note_off', note=p, velocity=64, time=beat))
    mid.save(file=buf)
    buf.seek(0)
    return buf


def _signup(client, email="tester@example.com", password="password1"):
    """注册并返回 access_token"""
    r = client.post("/api/v1/auth/signup", json={
        "email": email, "password": password, "age": 30,
    })
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


# ──────────────────────────────────────────────
# POST /evaluations
# ──────────────────────────────────────────────
def test_create_evaluation_success(client):
    """上传 MIDI → 创建评估 → 返回 5 维 + tips"""
    token = _signup(client)
    midi_bytes = _create_midi_bytes([60, 62, 64, 65, 67])

    r = client.post(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "piece_name": "Test Piece",
            "piece_composer": "Test Composer",
            "difficulty": "elementary",
            "period_hint": "baroque",
        },
        files={"midi_file": ("test.mid", midi_bytes, "audio/midi")},
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert "evaluation" in data
    eval_obj = data["evaluation"]
    assert eval_obj["piece_name"] == "Test Piece"
    assert eval_obj["piece_composer"] == "Test Composer"
    assert eval_obj["difficulty"] == "elementary"
    assert eval_obj["midi_size_bytes"] > 0
    # 5 维分数
    assert 0.0 <= eval_obj["pitch_score"] <= 1.0
    assert 0.0 <= eval_obj["expressiveness_score"] <= 1.0
    # 无 ref_midi → pitch/rhythm 都是 0
    assert eval_obj["pitch_score"] == 0.0
    assert eval_obj["rhythm_score"] == 0.0
    # 教学建议
    assert isinstance(data["tips"], list)
    assert len(data["tips"]) > 0
    # overall = 5 维加权
    assert 0.0 <= eval_obj["overall_score"] <= 1.0


def test_create_evaluation_requires_auth(client):
    """无 token → 401/403"""
    midi_bytes = _create_midi_bytes([60, 62, 64])
    r = client.post(
        "/api/v1/evaluations",
        data={"piece_name": "X"},
        files={"midi_file": ("x.mid", midi_bytes, "audio/midi")},
    )
    assert r.status_code in (401, 403)


def test_create_evaluation_missing_piece_name(client):
    """缺 piece_name → 422"""
    token = _signup(client, email="b@example.com")
    midi_bytes = _create_midi_bytes([60])
    r = client.post(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token}"},
        data={},  # 没 piece_name
        files={"midi_file": ("x.mid", midi_bytes, "audio/midi")},
    )
    assert r.status_code == 422


def test_create_evaluation_empty_midi(client):
    """空 MIDI → 评估可能失败但不崩"""
    token = _signup(client, email="c@example.com")
    r = client.post(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token}"},
        data={"piece_name": "Empty"},
        files={"midi_file": ("empty.mid", io.BytesIO(b""), "audio/midi")},
    )
    # 应该 201(异常隔离),评估分都是 0
    assert r.status_code == 201
    data = r.json()
    assert data["evaluation"]["overall_score"] >= 0.0


# ──────────────────────────────────────────────
# GET /evaluations/{id}
# ──────────────────────────────────────────────
def test_get_evaluation_by_id(client):
    """创建后按 ID 查"""
    token = _signup(client, email="d@example.com")
    midi_bytes = _create_midi_bytes([60, 62, 64, 65, 67, 69, 71, 72])

    r1 = client.post(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token}"},
        data={"piece_name": "Bach Prelude"},
        files={"midi_file": ("bach.mid", midi_bytes, "audio/midi")},
    )
    eval_id = r1.json()["evaluation"]["id"]

    r2 = client.get(
        f"/api/v1/evaluations/{eval_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["id"] == eval_id
    assert r2.json()["piece_name"] == "Bach Prelude"


def test_get_evaluation_not_found(client):
    """不存在的 ID → 404"""
    token = _signup(client, email="e@example.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(
        f"/api/v1/evaluations/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


def test_get_evaluation_other_user_forbidden(client):
    """别人的评估 → 403"""
    token_a = _signup(client, email="fa@example.com")
    token_b = _signup(client, email="fb@example.com")
    midi_bytes = _create_midi_bytes([60, 62, 64])

    r1 = client.post(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token_a}"},
        data={"piece_name": "Mine"},
        files={"midi_file": ("x.mid", midi_bytes, "audio/midi")},
    )
    eval_id = r1.json()["evaluation"]["id"]

    r2 = client.get(
        f"/api/v1/evaluations/{eval_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r2.status_code == 403


# ──────────────────────────────────────────────
# GET /evaluations/history
# ──────────────────────────────────────────────
def test_list_evaluations_history_empty(client):
    """无评估 → 空列表"""
    token = _signup(client, email="h1@example.com")
    r = client.get(
        "/api/v1/evaluations/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["skip"] == 0
    assert data["limit"] == 20


def test_list_evaluations_history_pagination(client):
    """分页:创建 5 个,limit 2 → 2 + 2 + 1"""
    token = _signup(client, email="h2@example.com")
    midi_bytes = _create_midi_bytes([60, 62, 64])

    for i in range(5):
        client.post(
            "/api/v1/evaluations",
            headers={"Authorization": f"Bearer {token}"},
            data={"piece_name": f"Piece {i}"},
            files={"midi_file": (f"x{i}.mid", midi_bytes, "audio/midi")},
        )

    # First page
    r1 = client.get(
        "/api/v1/evaluations/history?skip=0&limit=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200
    assert len(r1.json()["items"]) == 2
    assert r1.json()["total"] == 5

    # Last page
    r2 = client.get(
        "/api/v1/evaluations/history?skip=4&limit=2",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert len(r2.json()["items"]) == 1


def test_list_evaluations_only_own(client):
    """只返回自己的评估"""
    token_a = _signup(client, email="ha@example.com")
    token_b = _signup(client, email="hb@example.com")
    midi_bytes = _create_midi_bytes([60])

    client.post(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token_a}"},
        data={"piece_name": "A1"},
        files={"midi_file": ("a.mid", midi_bytes, "audio/midi")},
    )
    client.post(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token_a}"},
        data={"piece_name": "A2"},
        files={"midi_file": ("a.mid", midi_bytes, "audio/midi")},
    )
    client.post(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token_b}"},
        data={"piece_name": "B1"},
        files={"midi_file": ("b.mid", midi_bytes, "audio/midi")},
    )

    r_a = client.get(
        "/api/v1/evaluations/history",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    r_b = client.get(
        "/api/v1/evaluations/history",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r_a.json()["total"] == 2
    assert r_b.json()["total"] == 1
    # A 看不到 B 的
    assert all("B1" not in item["piece_name"] for item in r_a.json()["items"])


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
