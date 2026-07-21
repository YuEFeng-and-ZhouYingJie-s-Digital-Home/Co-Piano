"""
LLM Proxy — Qwen 本地 + OpenAI 兜底
======================================

提供:
- generate(prompt, system=None, **kwargs) → LLMResponse
- stream(prompt, system=None, **kwargs) → AsyncIterator[str]
- generate_feedback(evaluation, dimensions) → str   # 5 维评估 → LLM 反馈

支持后端:
1. Qwen 本地 (settings.qwen_api_url,默认 http://localhost:8080)
2. OpenAI 兼容 (settings.openai_api_key + openai_model)
3. Mock (test 模式)

回退策略:Qwen 失败 → 自动切 OpenAI(若配置 key)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any, AsyncIterator, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("copiano.llm")


@dataclass
class LLMResponse:
    """LLM 响应统一格式"""
    content: str
    model: str
    backend: str  # "qwen" | "openai" | "mock"
    latency_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    finish_reason: str = "stop"

    def to_dict(self) -> dict:
        return asdict(self)


class LLMService:
    """LLM 代理服务"""

    def __init__(self) -> None:
        self._qwen_url = settings.qwen_api_url.rstrip("/")
        self._openai_key = settings.openai_api_key
        self._openai_model = "gpt-4o-mini"  # 默认

    async def _call_qwen(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """调 Qwen 本地 (兼容 OpenAI API)"""
        url = f"{self._qwen_url}/v1/chat/completions"
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": "qwen2.5-7b-instruct",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
        latency = int((time.perf_counter() - start) * 1000)

        if response.status_code != 200:
            raise RuntimeError(
                f"Qwen API error {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", "qwen2.5-7b-instruct"),
            backend="qwen",
            latency_ms=latency,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def _call_openai(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """调 OpenAI 兼容 API"""
        if not self._openai_key:
            raise RuntimeError("OpenAI key not configured")

        url = "https://api.openai.com/v1/chat/completions"
        if settings.openai_api_key.startswith("sk-test"):
            url = "https://api.openai.com/v1/chat/completions"

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {self._openai_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._openai_model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        start = time.perf_counter()
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
        latency = int((time.perf_counter() - start) * 1000)

        if response.status_code != 200:
            raise RuntimeError(
                f"OpenAI API error {response.status_code}: {response.text[:200]}"
            )

        data = response.json()
        choice = data["choices"][0]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice["message"]["content"],
            model=data.get("model", self._openai_model),
            backend="openai",
            latency_ms=latency,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            total_tokens=usage.get("total_tokens", 0),
            finish_reason=choice.get("finish_reason", "stop"),
        )

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        prefer: str = "qwen",
    ) -> LLMResponse:
        """生成 LLM 响应(主后端失败自动回退)"""
        # 优先级:prefer > qwen > openai
        order = [prefer] if prefer != "auto" else ["qwen", "openai"]
        for backend in order + ["openai"] if "openai" not in order else []:
            try:
                if backend == "qwen":
                    return await self._call_qwen(prompt, system, max_tokens, temperature)
                elif backend == "openai":
                    return await self._call_openai(prompt, system, max_tokens, temperature)
            except Exception as e:
                logger.warning("llm_backend_failed backend=%s error=%s", backend, e)
                continue
        # 都失败
        raise RuntimeError("All LLM backends failed")

    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        max_tokens: int = 512,
        temperature: float = 0.7,
        prefer: str = "qwen",
    ) -> AsyncIterator[str]:
        """流式生成(每次 yield 一段文本)"""
        response = await self.generate(
            prompt, system, max_tokens, temperature, prefer
        )
        # 简化:一次性 yield 全部(v1.0 不实现真 streaming,避免复杂)
        yield response.content

    # ──────────────────────────────────────────────
    # 业务级辅助:5 维评估 → LLM 反馈
    # ──────────────────────────────────────────────
    async def generate_feedback(
        self,
        evaluation: dict,
        user_age: Optional[int] = None,
    ) -> LLMResponse:
        """根据 5 维评估分数 + 弱点生成教学反馈

        evaluation: {
            "piece_name": "Bach Prelude",
            "pitch_score": 0.9,
            "expressiveness_score": 0.7,
            "hand_pose_score": 0.5,  # 弱点
            "rhythm_score": 0.85,
            "sight_reading_score": 0.6,
            "overall_score": 0.78,
        }
        """
        # 构造 prompt
        dims = {
            "音准 (pitch)": evaluation.get("pitch_score", 0),
            "表现力 (expressiveness)": evaluation.get("expressiveness_score", 0),
            "手型 (hand_pose)": evaluation.get("hand_pose_score", 0),
            "节奏 (rhythm)": evaluation.get("rhythm_score", 0),
            "视奏 (sight_reading)": evaluation.get("sight_reading_score", 0),
        }
        sorted_dims = sorted(dims.items(), key=lambda x: x[1])
        weakest = sorted_dims[0]
        strongest = sorted_dims[-1]

        # 银发用户用简化 prompt
        is_senior = user_age is not None and user_age >= 60
        if is_senior:
            system = "你是一位耐心的钢琴老师,用简单易懂的语言给老年学员反馈。每次回复 2-3 句话,鼓励为主。"
        else:
            system = "你是一位专业的钢琴老师,根据学员的 5 维评估给出具体、有建设性的反馈。用 3-5 句话,既要肯定优点也要指出可改进的地方。"

        prompt = f"""学员演奏了《{evaluation.get('piece_name', '未知曲目')}》,综合分 {evaluation.get('overall_score', 0):.0%}。

5 维分数:
{chr(10).join(f'  - {k}: {v:.0%}' for k, v in dims.items())}

最强:{strongest[0]} {strongest[1]:.0%}
最弱:{weakest[0]} {weakest[1]:.0%}

请给出简短反馈。"""

        return await self.generate(
            prompt=prompt, system=system, max_tokens=300, temperature=0.7,
        )


# Singleton
llm_service = LLMService()
