"""
Feedback Schemas — LLM 教学反馈
===================================
"""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class FeedbackRequest(BaseModel):
    """LLM 反馈请求"""
    evaluation_id: uuid.UUID = Field(..., description="评估 ID")
    prefer: str = Field(
        default="qwen",
        description="后端偏好: qwen | openai | auto",
    )
    max_tokens: int = Field(default=300, ge=50, le=2000)


class FeedbackResponse(BaseModel):
    """LLM 反馈响应"""
    evaluation_id: str
    feedback: str
    model: str
    backend: str  # qwen | openai
    latency_ms: int
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    created_at: datetime

    @field_validator("evaluation_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class FeedbackHistoryItem(BaseModel):
    """历史反馈列表项"""
    evaluation_id: str
    feedback_preview: str  # 前 100 字
    model: str
    created_at: datetime

    @field_validator("evaluation_id", mode="before")
    @classmethod
    def _uuid_to_str(cls, v):
        if isinstance(v, uuid.UUID):
            return str(v)
        return v


class FeedbackHistoryResponse(BaseModel):
    """历史反馈列表"""
    items: list[FeedbackHistoryItem]
    total: int
