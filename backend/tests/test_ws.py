"""
WebSocket LLM tests
====================

用 TestClient 测试 WebSocket 端点
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

    # 同时 patch get_async_session_factory 供 WebSocket 使用
    from app.db import base as db_base
    original_factory = db_base._async_session_factory
    db_base._async_session_factory = factory
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()
        db_base._async_session_factory = original_factory


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


def _signup(client, email):
    r = client.post("/api/v1/auth/signup", json={"email": email, "password": "password1"})
    return r.json()["access_token"]


def _create_evaluation(client, token, piece="Bach"):
    midi = _create_midi_bytes([60, 62, 64, 65, 67])
    r = client.post(
        "/api/v1/evaluations",
        headers={"Authorization": f"Bearer {token}"},
        data={"piece_name": piece, "difficulty": "elementary"},
        files={"midi_file": ("x.mid", midi, "audio/midi")},
    )
    return r.json()["evaluation"]["id"]


def _mock_llm(content="WebSocket test feedback"):
    async def fake(*args, **kwargs):
        return LLMResponse(
            content=content,
            model="qwen2.5-7b-instruct",
            backend="qwen",
            latency_ms=300,
            prompt_tokens=50,
            completion_tokens=25,
            total_tokens=75,
        )
    return fake


# ──────────────────────────────────────────────
# WebSocket tests
# ──────────────────────────────────────────────
def test_ws_unauthorized_no_token(client):
    """无 token → 1008 Policy Violation(由 FastAPI 验证层处理)"""
    # FastAPI WebSocket 必传 token query param,缺则直接拒绝
    with pytest.raises(Exception):  # WebSocketDisconnect 或 starlette 异常
        with client.websocket_connect("/api/v1/ws/llm?evaluation_id=00000000-0000-0000-0000-000000000000"):
            pass


def test_ws_unauthorized_invalid_token(client):
    """无效 token → 服务端返回 error + 关闭"""
    with client.websocket_connect(
        "/api/v1/ws/llm?token=invalid_token&evaluation_id=00000000-0000-0000-0000-000000000000"
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "Unauthorized" in msg["message"]


def test_ws_invalid_evaluation_id(client):
    """无效 evaluation_id UUID"""
    token = _signup(client, "ws1@example.com")
    with client.websocket_connect(
        f"/api/v1/ws/llm?token={token}&evaluation_id=not-a-uuid"
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        # 服务端统一报"not found or not yours"
        assert "not found" in msg["message"].lower() or "invalid" in msg["message"].lower()


def test_ws_evaluation_not_found(client):
    """evaluation_id 不存在"""
    token = _signup(client, "ws2@example.com")
    fake_id = "00000000-0000-0000-0000-000000000000"
    with client.websocket_connect(
        f"/api/v1/ws/llm?token={token}&evaluation_id={fake_id}"
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "not found" in msg["message"].lower()


def test_ws_other_user_evaluation_forbidden(client):
    """别人的 evaluation_id → 403"""
    token_a = _signup(client, "wsa@example.com")
    token_b = _signup(client, "wsb@example.com")
    eval_id = _create_evaluation(client, token_a)

    with client.websocket_connect(
        f"/api/v1/ws/llm?token={token_b}&evaluation_id={eval_id}"
    ) as ws:
        msg = ws.receive_json()
        assert msg["type"] == "error"
        # 统一报"not found or not yours" (安全考虑,避免泄露存在)
        assert "not found" in msg["message"].lower() or "not yours" in msg["message"].lower()


def test_ws_success_streaming(client):
    """完整流式流程:chunk 序列 + done"""
    token = _signup(client, "wsc@example.com")
    eval_id = _create_evaluation(client, token)

    with patch(
        "app.api.v1.ws.llm_service.generate_feedback",
        new=AsyncMock(side_effect=_mock_llm("Mocked streaming feedback content here")),
    ):
        with client.websocket_connect(
            f"/api/v1/ws/llm?token={token}&evaluation_id={eval_id}"
        ) as ws:
            # 接收所有消息
            messages = []
            while True:
                msg = ws.receive_json()
                messages.append(msg)
                if msg["type"] in ("done", "error"):
                    break

    # 至少 1 个 chunk + 1 个 done
    chunks = [m for m in messages if m["type"] == "chunk"]
    done = [m for m in messages if m["type"] == "done"]
    assert len(chunks) >= 1
    assert len(done) == 1
    assert done[0]["backend"] == "qwen"
    assert done[0]["total_tokens"] == 75

    # 拼接 chunks 应等于原 content
    full = "".join(c["content"] for c in chunks)
    assert full == "Mocked streaming feedback content here"


def test_ws_short_content_single_chunk(client):
    """短内容(< chunk_size) → 单 chunk"""
    token = _signup(client, "wsd@example.com")
    eval_id = _create_evaluation(client, token)

    with patch(
        "app.api.v1.ws.llm_service.generate_feedback",
        new=AsyncMock(side_effect=_mock_llm("短")),
    ):
        with client.websocket_connect(
            f"/api/v1/ws/llm?token={token}&evaluation_id={eval_id}"
        ) as ws:
            messages = []
            while True:
                msg = ws.receive_json()
                messages.append(msg)
                if msg["type"] in ("done", "error"):
                    break
    chunks = [m for m in messages if m["type"] == "chunk"]
    # 1 个 chunk (中文也按字符切,虽然只有 1 字符但 chunk_size=20 不会切)
    assert len(chunks) == 1
    assert chunks[0]["content"] == "短"


def test_ws_llm_failure_error_message(client):
    """LLM 失败 → error 消息"""
    token = _signup(client, "wse@example.com")
    eval_id = _create_evaluation(client, token)

    with patch(
        "app.api.v1.ws.llm_service.generate_feedback",
        new=AsyncMock(side_effect=RuntimeError("All LLM backends failed")),
    ):
        with client.websocket_connect(
            f"/api/v1/ws/llm?token={token}&evaluation_id={eval_id}"
        ) as ws:
            msg = ws.receive_json()
            assert msg["type"] == "error"
            assert "All LLM backends failed" in msg["message"]


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
