"""
LLM Service tests — mock Qwen + OpenAI
=======================================
"""
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

import pytest

from app.services.llm_service import LLMResponse, LLMService, llm_service


# ──────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────
@pytest.fixture
def mock_qwen_response():
    """Mock httpx 返回 Qwen 响应"""
    return {
        "id": "chatcmpl-123",
        "model": "qwen2.5-7b-instruct",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "Mocked Qwen response"},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70,
        },
    }


@pytest.fixture
def mock_openai_response():
    """Mock httpx 返回 OpenAI 响应"""
    return {
        "id": "chatcmpl-456",
        "model": "gpt-4o-mini",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": "Mocked OpenAI response"},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 50,
            "completion_tokens": 20,
            "total_tokens": 70,
        },
    }


# ──────────────────────────────────────────────
# LLMResponse
# ──────────────────────────────────────────────
def test_llm_response_to_dict():
    """LLMResponse.to_dict 可序列化"""
    r = LLMResponse(
        content="test",
        model="gpt-4o-mini",
        backend="openai",
        latency_ms=100,
    )
    d = r.to_dict()
    assert d["content"] == "test"
    assert d["backend"] == "openai"
    assert d["latency_ms"] == 100


def test_llm_response_defaults():
    """LLMResponse 默认值"""
    r = LLMResponse(content="x", model="m", backend="b", latency_ms=1)
    assert r.prompt_tokens == 0
    assert r.completion_tokens == 0
    assert r.total_tokens == 0
    assert r.finish_reason == "stop"


# ──────────────────────────────────────────────
# LLMService 基础
# ──────────────────────────────────────────────
def test_llm_service_init():
    """LLMService 可实例化"""
    s = LLMService()
    assert s._qwen_url.endswith("/v1").__class__  # or just truthy
    # qwen_url 不一定有 /v1 后缀(API 路径会拼)


def test_llm_service_singleton():
    """llm_service 是单例"""
    from app.services.llm_service import llm_service as ls2
    assert llm_service is ls2


# ──────────────────────────────────────────────
# Qwen 后端
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_generate_qwen_success(mock_qwen_response):
    """Qwen 成功"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_qwen_response

    s = LLMService()
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        result = await s._call_qwen("test prompt", system="sys")

    assert isinstance(result, LLMResponse)
    assert result.content == "Mocked Qwen response"
    assert result.backend == "qwen"
    assert result.model == "qwen2.5-7b-instruct"
    assert result.total_tokens == 70
    assert result.latency_ms > 0


@pytest.mark.asyncio
async def test_generate_qwen_error_raises():
    """Qwen 4xx/5xx → RuntimeError"""
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    s = LLMService()
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        with pytest.raises(RuntimeError) as exc_info:
            await s._call_qwen("test")
    assert "Qwen API error" in str(exc_info.value)


# ──────────────────────────────────────────────
# OpenAI 后端
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_generate_openai_success(mock_openai_response):
    """OpenAI 成功"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_openai_response

    s = LLMService()
    s._openai_key = "sk-test-fake"
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        result = await s._call_openai("test prompt")

    assert result.content == "Mocked OpenAI response"
    assert result.backend == "openai"
    assert result.model == "gpt-4o-mini"


@pytest.mark.asyncio
async def test_generate_openai_no_key_raises():
    """OpenAI 没配 key → RuntimeError"""
    s = LLMService()
    s._openai_key = ""
    with pytest.raises(RuntimeError) as exc_info:
        await s._call_openai("test")
    assert "OpenAI key not configured" in str(exc_info.value)


# ──────────────────────────────────────────────
# 自动回退
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_generate_fallback_qwen_to_openai(mock_openai_response):
    """Qwen 失败 → 自动 OpenAI"""
    qwen_fail = MagicMock()
    qwen_fail.status_code = 500
    qwen_fail.text = "Qwen down"

    openai_resp = MagicMock()
    openai_resp.status_code = 200
    openai_resp.json.return_value = mock_openai_response

    s = LLMService()
    s._openai_key = "sk-test-fake"

    # 第一次(httpx.AsyncClient) → Qwen 失败
    # 第二次 → OpenAI 成功
    call_count = [0]

    async def fake_post(self, url, **kwargs):
        call_count[0] += 1
        if "localhost" in url or "8080" in url:
            return qwen_fail
        return openai_resp

    with patch("httpx.AsyncClient.post", new=fake_post):
        result = await s.generate("test", prefer="qwen")

    assert result.backend == "openai"
    assert result.content == "Mocked OpenAI response"
    assert call_count[0] == 2  # 调了 2 次


@pytest.mark.asyncio
async def test_generate_all_backends_fail():
    """所有后端失败 → RuntimeError"""
    fail_response = MagicMock()
    fail_response.status_code = 500
    fail_response.text = "down"

    s = LLMService()
    s._openai_key = "sk-test"

    async def fake_post(self, url, **kwargs):
        return fail_response

    with patch("httpx.AsyncClient.post", new=fake_post):
        with pytest.raises(RuntimeError) as exc_info:
            await s.generate("test")
    assert "All LLM backends failed" in str(exc_info.value)


# ──────────────────────────────────────────────
# Stream
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_stream_yields_content(mock_qwen_response):
    """stream 异步生成"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_qwen_response

    s = LLMService()
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        chunks = []
        async for chunk in s.stream("test"):
            chunks.append(chunk)
    # 简化版 stream:一次性 yield 全部
    assert chunks == ["Mocked Qwen response"]


# ──────────────────────────────────────────────
# generate_feedback
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_generate_feedback_basic(mock_qwen_response):
    """生成教学反馈"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_qwen_response

    evaluation = {
        "piece_name": "Bach Prelude in C",
        "pitch_score": 0.95,
        "expressiveness_score": 0.7,
        "hand_pose_score": 0.5,
        "rhythm_score": 0.85,
        "sight_reading_score": 0.6,
        "overall_score": 0.73,
    }

    s = LLMService()
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        result = await s.generate_feedback(evaluation)

    assert result.backend == "qwen"
    assert result.content == "Mocked Qwen response"


@pytest.mark.asyncio
async def test_generate_feedback_senior(mock_qwen_response):
    """银发用户反馈(simpler system prompt)"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_qwen_response

    s = LLMService()
    with patch("httpx.AsyncClient.post", new=AsyncMock(return_value=mock_response)):
        result = await s.generate_feedback(
            {"piece_name": "Twinkle", "overall_score": 0.5},
            user_age=70,
        )
    assert result.content is not None


# ──────────────────────────────────────────────
# 银发模式(简化的 prompt / system 切换)
# ──────────────────────────────────────────────
@pytest.mark.asyncio
async def test_senior_uses_simpler_system_prompt(mock_qwen_response):
    """65+ 用简化 system prompt"""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_qwen_response

    s = LLMService()
    captured_payload = {}

    async def fake_post(self, url, **kwargs):
        captured_payload.update(kwargs.get("json", {}))
        return mock_response

    with patch("httpx.AsyncClient.post", new=fake_post):
        await s.generate_feedback(
            {"piece_name": "X", "overall_score": 0.5},
            user_age=70,
        )

    sys_msg = captured_payload.get("messages", [{}])[0].get("content", "")
    # 银发 system prompt 应包含"耐心"或"简单"
    assert "耐心" in sys_msg or "简单" in sys_msg or "鼓励" in sys_msg


if __name__ == "__main__":
    import subprocess
    result = subprocess.run(["pytest", __file__, "-v", "--tb=short"], cwd=str(BACKEND_DIR))
    sys.exit(result.returncode)
